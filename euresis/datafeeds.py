"""Data feeds: Euresis connects to published research datasets and searches them for laws.

Online, it queries open research-data repositories where datasets are attached to papers
and carry a DOI — Zenodo, Figshare, Dryad — downloads small tabular files (CSV), and
analyses every pair of numeric columns. Offline (or when a source is unreachable) it
falls back to datasets already on disk, so discovery never stops.

For each pair (x, y) it fits the law forms Euresis knows (linear, power law
y = a·x^b, exponential y = a·e^{bx}, logarithmic) on a random half of the rows, and
keeps a relation only if it is strong on that half (R² ≥ 0.9) AND holds on the
held-out half (R² ≥ 0.85, same form and sign). Trivial relations are removed:
duplicated or rescaled columns, unit conversions, identifiers and row indices.
Every finding goes through the verification gate (claim kind ``empirical``, which
re-runs the test on the held-out rows) and records the dataset's DOI and title, so a
person can trace it to the paper. These are empirical regularities — evidence, not
proof — and many will be known to the dataset's authors.
"""
from __future__ import annotations

import hashlib
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from .registry import ROOT, Registry, atomic_write

CACHE = ROOT / "data" / "feeds"
STATE = ROOT / "space" / "datafeeds_state.json"
LOG = ROOT / "space" / "datafeeds_log.md"
MAX_BYTES = 15_000_000
UA = {"User-Agent": "Euresis-discovery/0.2 (research data analysis)"}
QUERIES = ["measurements", "experimental data", "physics", "chemistry", "ecology", "astronomy", "materials",
           "climate", "biology", "engineering", "economics", "geology", "oceanography", "hydrology", "soil"]


def log(msg, echo=print):
    echo(msg)
    with LOG.open("a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


def _get(url: str, timeout=30, limit: int | None = None) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit + 1 if limit else -1)


def online() -> bool:
    try:
        _get("https://zenodo.org/api/records?size=1", timeout=10)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ sources
def search_zenodo(query: str, page: int = 1, size: int = 25) -> list[dict]:
    q = urllib.parse.quote(f"{query} AND resource_type.type:dataset AND filetype:csv")
    d = json.loads(_get(f"https://zenodo.org/api/records?q={q}&size={size}&page={page}&sort=bestmatch"))
    out = []
    for h in d.get("hits", {}).get("hits", []):
        md = h.get("metadata", {})
        for f in h.get("files", []):
            key = f.get("key", "")
            if key.lower().endswith(".csv") and 0 < f.get("size", 0) <= MAX_BYTES:
                out.append({"source": "Zenodo", "doi": h.get("doi") or md.get("doi", ""), "title": md.get("title", ""),
                            "file": key, "url": f.get("links", {}).get("self", ""), "size": f.get("size", 0),
                            "related": [r.get("identifier") for r in md.get("related_identifiers", [])][:3]})
    return out


def search_figshare(query: str, page: int = 1, size: int = 20) -> list[dict]:
    body = json.dumps({"search_for": query, "item_type": 3, "page": page, "page_size": size}).encode()
    req = urllib.request.Request("https://api.figshare.com/v2/articles/search", data=body,
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        arts = json.loads(r.read())
    out = []
    for a in arts:
        try:
            det = json.loads(_get(f"https://api.figshare.com/v2/articles/{a['id']}"))
        except Exception:
            continue
        for f in det.get("files", []):
            if f.get("name", "").lower().endswith(".csv") and 0 < f.get("size", 0) <= MAX_BYTES:
                out.append({"source": "Figshare", "doi": det.get("doi", ""), "title": det.get("title", ""),
                            "file": f["name"], "url": f.get("download_url", ""), "size": f["size"],
                            "related": [det.get("resource_doi")] if det.get("resource_doi") else []})
    return out


def local_datasets() -> list[dict]:
    """Datasets already on disk: always available offline."""
    out = []
    oec = ROOT / "data" / "external" / "oec.csv"
    if oec.exists():
        out.append({"source": "local", "doi": "", "title": "Open Exoplanet Catalogue", "file": "oec.csv",
                    "url": str(oec), "size": oec.stat().st_size, "related": []})
    for p in sorted(CACHE.glob("*.csv")):
        meta = p.with_suffix(".json")
        if meta.exists():
            out.append(json.loads(meta.read_text()))
    return out


def fetch(item: dict) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1((item["doi"] + item["file"]).encode()).hexdigest()[:16]
    path = CACHE / f"{key}.csv"
    if item["source"] == "local":
        return Path(item["url"])
    if not path.exists():
        data = _get(item["url"], timeout=60, limit=MAX_BYTES)
        if len(data) > MAX_BYTES:
            return None
        path.write_bytes(data)
        path.with_suffix(".json").write_text(json.dumps({**item, "url": str(path), "source_url": item["url"],
                                                         "source": item["source"]}))
    return path


# ------------------------------------------------------------------ analysis
FORMS = ("linear", "power law", "exponential", "logarithmic")


def _fit(form, x, y):
    """Returns (params, transformed x, transformed y) for a linear fit in transformed space, or None."""
    with np.errstate(all="ignore"):
        if form == "linear":
            X, Y = x, y
        elif form == "power law":
            if (x <= 0).any() or (y <= 0).any():
                return None
            X, Y = np.log(x), np.log(y)
        elif form == "exponential":
            if (y <= 0).any():
                return None
            X, Y = x, np.log(y)
        else:
            if (x <= 0).any():
                return None
            X, Y = np.log(x), y
    if not (np.isfinite(X).all() and np.isfinite(Y).all()) or np.std(X) == 0 or np.std(Y) == 0:
        return None
    b, a = np.polyfit(X, Y, 1)
    return (a, b), X, Y


def r2(form, params, x, y):
    f = _fit(form, x, y)
    if f is None:
        return -np.inf
    (_, _), X, Y = f
    a, b = params
    pred = a + b * X
    ss = ((Y - Y.mean()) ** 2).sum()
    return float(1 - ((Y - pred) ** 2).sum() / ss) if ss > 0 else -np.inf


def load_table(path: Path):
    import pandas as pd
    raw = path.read_bytes()[:MAX_BYTES]
    for sep in (",", ";", "\t"):
        try:
            df = pd.read_csv(io.BytesIO(raw), sep=sep, low_memory=False)
        except Exception:
            continue
        if df.shape[1] >= 2:
            break
    else:
        return None
    def _num(v):
        try:
            float(str(v))
            return True
        except ValueError:
            return False
    if all(_num(c) for c in df.columns):           # no header row: the first data row was read as names
        df = pd.read_csv(io.BytesIO(raw), sep=sep, header=None, low_memory=False)
        df.columns = [f"column {i + 1} (unlabelled)" for i in range(df.shape[1])]
    num = df.apply(pd.to_numeric, errors="coerce")
    keep = [c for c in num.columns if num[c].notna().mean() > 0.9 and num[c].nunique() > 10]
    num = num[keep]
    # drop identifiers / row indices: strictly increasing integer columns
    num = num[[c for c in num.columns if not (np.all(np.diff(num[c].dropna().values) > 0) and
                                              np.allclose(num[c].dropna() % 1, 0))]]
    return num.dropna().iloc[:20000, :15]


def split(n, seed):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    return idx[: n // 2], idx[n // 2:]


_SEEN_PAIRS: set = set()
_PHRASE = {"linear": "is linear", "power law": "follows a power law", "exponential": "grows exponentially",
           "logarithmic": "grows logarithmically"}


def analyse(path: Path, item: dict, reg: Registry, echo=print) -> list[dict]:
    from . import gate
    T = load_table(path)
    if T is None or T.shape[0] < 60 or T.shape[1] < 2:
        return []
    seed = int(hashlib.sha1(str(path).encode()).hexdigest()[:8], 16)
    A, B = split(len(T), seed)
    cols = list(T.columns)
    found = []
    for i, cx in enumerate(cols):
        for cy in cols[i + 1:]:
            x, y = T[cx].values.astype(float), T[cy].values.astype(float)
            # trivial: the same quantity twice (duplicate, rescaled or shifted column)
            if abs(np.corrcoef(x, y)[0, 1]) > 0.995:
                continue                      # the same quantity measured twice (e.g. left/right, duplicate sensors)
            names = {str(cx).strip().lower(), str(cy).strip().lower()}
            if names & {"se", "sem", "standard error", "std_err", "stderr"} and names & {"n", "sample size", "n_total", "size"}:
                continue                      # SE = σ/√n: a statistical identity, not a law
            order = np.arange(len(x))
            if all(abs(np.corrcoef(np.argsort(np.argsort(v)), order)[0, 1]) > 0.98 for v in (x, y)):
                continue                      # both columns just increase down the table (timestamps, counters)
            key = f"{item.get('doi')}|{cx}|{cy}"
            if key in _SEEN_PAIRS:
                continue                      # same relation already found in another file of this dataset
            _SEEN_PAIRS.add(key)
            best = None
            for form in FORMS:
                f = _fit(form, x[A], y[A])
                if f is None:
                    continue
                params = f[0]
                s = r2(form, params, x[A], y[A])
                if best is None or s > best[2]:
                    best = (form, params, s)
            if best is None or best[2] < 0.9 or best[2] > 0.99999:
                continue                      # weak, or an exact (definitional) relation
            form, params, sA = best
            payload = {"dataset": str(path.name), "x": str(cx), "y": str(cy), "form": form, "seed": seed,
                       "params": [float(params[0]), float(params[1])], "doi": item.get("doi", "")}
            stmt = (f"In '{item.get('title', '')[:90]}' ({item.get('source')}{', doi ' + item['doi'] if item.get('doi') else ''}): "
                    f"'{cy}' {_PHRASE[form]} in '{cx}' (R² = {sA:.3f} on the discovery half)")
            cid = reg.add("empirical", stmt, payload, source="datafeeds.py")
            if gate.check(reg, cid, log=lambda *a: None) != "verified-numeric":
                continue
            ev = reg.get(cid)["evidence"]
            unl = "unlabelled" in cx + cy
            reg.set_novelty(cid, "empirical regularity in a published dataset; probably known to its authors — "
                                 "check the linked paper; units unknown, so not a law until interpreted"
                            + ("; the file has no column names — the dataset's documentation is needed to say what "
                               "the columns are" if unl else ""))
            rec = {"claim": cid, "statement": stmt, "held_out_r2": ev.get("held_out_r2")}
            found.append(rec)
            log(f"FINDING (confirmed on held-out rows): {stmt}; held-out R² = {ev.get('held_out_r2'):.3f} [{cid}]", echo)
    return found


def verify_claim(p: dict) -> tuple[str, dict]:
    """Re-run the fit on the held-out half of the rows."""
    path = CACHE / p["dataset"] if (CACHE / p["dataset"]).exists() else ROOT / "data" / "external" / p["dataset"]
    if not path.exists():
        return "unverified", {"reason": "dataset not available on this machine"}
    T = load_table(path)
    A, B = split(len(T), p["seed"])
    x, y = T[p["x"]].values.astype(float), T[p["y"]].values.astype(float)
    sB = r2(p["form"], p["params"], x[B], y[B])
    ok = sB >= 0.85
    return ("verified-numeric" if ok else "refuted"), {
        "held_out_r2": round(sB, 4), "held_out_rows": int(len(B)), "doi": p.get("doi", ""),
        "note": "empirical confirmation on held-out rows — evidence, not proof"}


# ------------------------------------------------------------------ loop
def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"seen": [], "findings": [], "query_pos": 0,
                                                                "page": 1}


def run(minutes: float = 30, echo=print, reg: Registry | None = None) -> dict:
    reg = reg or Registry()
    st = load_state()
    _SEEN_PAIRS.update(st.get("pairs", []))
    t0 = time.time()
    net = online()
    log(f"data feeds: {'online' if net else 'OFFLINE — using datasets on disk'}", echo)
    queue = []
    if net:
        while not queue and time.time() - t0 < minutes * 60:
            q = QUERIES[st["query_pos"] % len(QUERIES)]
            for src in (search_zenodo, search_figshare):
                try:
                    queue += [it for it in src(q, page=st["page"]) if (it["doi"] + it["file"]) not in st["seen"]]
                except Exception as e:
                    echo(f"  {src.__name__}: unavailable ({type(e).__name__})")
            st["query_pos"] += 1
            if st["query_pos"] % len(QUERIES) == 0:
                st["page"] += 1
            if not queue and st["query_pos"] > 10 * len(QUERIES):
                break
    if not queue:
        queue = [it for it in local_datasets() if ("local:" + it["file"]) not in st["seen"]] or local_datasets()
    for item in queue:
        if time.time() - t0 > minutes * 60:
            break
        key = (item["doi"] + item["file"]) if item["source"] != "local" else "local:" + item["file"]
        if key in st["seen"]:
            continue
        st["seen"].append(key)
        try:
            path = fetch(item)
            if path is None:
                continue
            echo(f"  dataset: {item['title'][:70]} [{item['source']}] — {item['file'][:40]}")
            st["findings"] += analyse(path, item, reg, echo)
        except Exception as e:
            echo(f"  skipped {item['file'][:40]}: {type(e).__name__}: {str(e)[:80]}")
        st["pairs"] = sorted(_SEEN_PAIRS)
        atomic_write(STATE, json.dumps(st) + "\n")
    st["pairs"] = sorted(_SEEN_PAIRS)
    atomic_write(STATE, json.dumps(st) + "\n")
    log(f"data feeds: {len(st['seen'])} datasets analysed so far, {len(st['findings'])} confirmed findings", echo)
    return st
