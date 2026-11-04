"""Open-ended discovery loop: runs until told to stop.

Each round:
  1. **Propose** — the local 14B model (Qwen3-14B) invents new symmetric,
     scale-invariant expressions E(a, b, c), minimised at a = b = c. It is shown
     what has been tried, proved and refuted so far, so it explores new ground.
     (Without the model, Euresis combines known expressions itself.)
  2. **Validate** — Euresis checks each proposal exactly: parses, symmetric,
     homogeneous of degree 0, minimum at a = b = c, not a duplicate.
  3. **Discover** — for each new expression P and each known Q, Euresis finds the
     best constant k* in  P − min P ≥ k*·(Q − min Q)  numerically and snaps it to
     an exact rational.
  4. **Prove** — the claim goes to the verification gate (Z3 decision procedure
     + 200 000-point cross-check + sharpness test). The gate alone decides.
  5. **Record** — every claim goes into the registry. A *discovery* is proved,
     sharp, and not known to Euresis. Novelty against the wider literature
     cannot be checked from this environment and is labelled as unchecked.

The loop never stops by itself. It stops when `data/STOP` exists
(`python -m euresis discover-new --stop`) or when a segment's time budget ends;
the next segment resumes from the saved state.
"""
from __future__ import annotations

import itertools
import json
import random
import re
import time
from pathlib import Path

import numpy as np
import sympy as sp

from . import gate, theorems
from .registry import ROOT, Registry

a, b, c = theorems.a, theorems.b, theorems.c
STATE = ROOT / "space" / "discovery_state.json"
LOG = ROOT / "space" / "discovery_log.md"
STOP = ROOT / "data" / "STOP"
NOVELTY = ("not in Euresis' knowledge or registry; not a classical inequality Euresis knows; "
           "wider literature unchecked (arXiv/OEIS unreachable from this environment)")


# ------------------------------------------------------------------ state
def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"expressions": {k: str(v) for k, v in theorems.LIBRARY.items()}, "rejected": [], "pairs_tried": [],
            "rounds": 0, "discoveries": [], "seconds": 0.0}


def save_state(st: dict):
    STATE.write_text(json.dumps(st, indent=1) + "\n")


def log(msg: str, echo=print):
    echo(msg)
    with LOG.open("a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


# ------------------------------------------------------------- validation
_SYM = {"a": a, "b": b, "c": c}


def validate(expr: str, known: dict) -> tuple[sp.Expr | None, str]:
    """Exact checks: symmetric, degree-0 homogeneous, minimised at a=b=c, new."""
    try:
        E = sp.sympify(expr.replace("^", "**"), locals=_SYM)
    except Exception:
        return None, "does not parse"
    if not isinstance(E, sp.Expr) or E.free_symbols - {a, b, c} or not E.free_symbols:
        return None, "must use only a, b, c"
    if not E.is_rational_function(a, b, c):
        return None, "must be a rational function (no roots or other functions) so the prover can decide it"
    if E.count_ops() > 60:
        return None, "too complicated"
    t = sp.Symbol("t", positive=True)
    if sp.simplify(E.subs({a: t * a, b: t * b, c: t * c}, simultaneous=True) - E) != 0:
        return None, "not scale-invariant (homogeneous of degree 0)"
    for perm in ((b, a, c), (a, c, b), (c, b, a)):
        if sp.simplify(E.subs(dict(zip((a, b, c), perm)), simultaneous=True) - E) != 0:
            return None, "not symmetric in a, b, c"
    f = sp.lambdify((a, b, c), E, "numpy")
    m = float(E.subs({a: 1, b: 1, c: 1}))
    rng = np.random.default_rng(0)
    pts = np.exp(rng.uniform(-3, 3, (3, 20000)))
    with np.errstate(all="ignore"):
        vals = np.asarray(f(*pts), float)
    if not np.all(np.isfinite(vals)):
        return None, "not finite for all positive a, b, c"
    if vals.min() < m - 1e-9:
        return None, "not minimised at a = b = c"
    if vals.max() - m < 1e-6:
        return None, "constant"
    why = derived_from(vals[:400], pts[:, :400], known)
    if why:
        return None, why
    return E, "ok"


def _known_values(known: dict, pts) -> dict:
    out = {}
    for name, ks in known.items():
        f = sp.lambdify((a, b, c), sp.sympify(ks, locals=_SYM), "numpy")
        with np.errstate(all="ignore"):
            out[name] = np.asarray(f(*pts), float)
    return out


def derived_from(vals, pts, known: dict) -> str:
    """Reject expressions that are just affine combinations or products of one or two known ones:
    inequalities about those tend to follow from known inequalities and are not discoveries."""
    K = _known_values(known, pts)
    names = list(K)
    one = np.ones_like(vals)
    scale = max(1.0, float(np.abs(vals).max()))
    for i, ni in enumerate(names):
        for nj in [None] + names[i:]:
            cols = [one, K[ni]] + ([K[nj]] if nj and nj != ni else [])
            A = np.stack(cols, 1)
            if not np.all(np.isfinite(A)):
                continue
            coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
            if np.abs(A @ coef - vals).max() < 1e-9 * scale:
                return f"affine combination of known expression(s) {ni}{' and ' + nj if nj and nj != ni else ''}"
            if nj:
                prod = K[ni] * K[nj]
                r = vals / prod
                if np.all(np.isfinite(r)) and r.max() - r.min() < 1e-9 * max(1.0, abs(r).max()):
                    return f"product of known expressions {ni} and {nj}"
    return ""


# --------------------------------------------------------------- proposals
PROPOSE_SYSTEM = (
    "You are the creative part of Euresis, a mathematical discovery system. You invent expressions; a theorem "
    "prover decides what is true. Output ONLY a JSON list of strings, nothing else.")


def propose_llm(st: dict, n: int = 6, echo=print) -> list[str]:
    from . import local_llm
    known = list(st["expressions"].values())
    rej = st["rejected"][-12:]
    msg = (f"Invent {n} NEW expressions E(a,b,c) in SymPy syntax (use ** for integer powers; no sqrt, no "
           "functions — only + - * / and integer powers) that are\n"
           "- symmetric in a, b, c,\n- homogeneous of degree 0 (unchanged when a, b, c are all multiplied by t),\n"
           "- finite for all positive a, b, c and minimised at a = b = c.\n"
           "Good building blocks: power sums a**k+b**k+c**k, ab+bc+ca, abc, (a+b)(b+c)(c+a), sums like "
           "a/(b+c)+..., ratios of means. Make them different from these known ones:\n"
           + "\n".join(f"  {k}" for k in known[-14:])
           + ("\nThese were rejected (reason in brackets) — avoid the same mistakes:\n"
              + "\n".join(f"  {r['expr']}  [{r['why']}]" for r in rej) if rej else "")
           + f"\nReply with a JSON list of {n} strings only.")
    r = local_llm.complete(PROPOSE_SYSTEM, [{"role": "user", "content": msg}], think=False, max_tokens=700,
                           temperature=0.9, log=echo)
    m = re.search(r"\[.*\]", r["text"], re.S)
    try:
        out = [s for s in json.loads(m.group(0)) if isinstance(s, str)] if m else []
    except json.JSONDecodeError:
        out = re.findall(r'"([^"]+)"', r["text"])
    echo(f"  model proposed {len(out)} expressions in {r['seconds']} s")
    return out[:n]


# symmetric building blocks with their degrees
_BLOCKS = {"p1": ("(a+b+c)", 1), "p2": ("(a**2+b**2+c**2)", 2), "p3": ("(a**3+b**3+c**3)", 3),
           "p4": ("(a**4+b**4+c**4)", 4), "e2": ("(a*b+b*c+c*a)", 2), "e3": ("(a*b*c)", 3),
           "q2": ("(a**2*b**2+b**2*c**2+c**2*a**2)", 4), "s3": ("((a+b)*(b+c)*(c+a))", 3),
           "m21": ("(a**2*b+a*b**2+b**2*c+b*c**2+c**2*a+c*a**2)", 3)}


def propose_structural(st: dict, n: int = 6) -> list[str]:
    """Without the model: ratios of products of symmetric building blocks of equal total degree,
    oriented so that the minimum is at a = b = c (e.g. p4·e2 / (p3·p1·... ))."""
    rng = random.Random(1000 + st["rounds"])
    names = list(_BLOCKS)
    out, tries = [], 0
    while len(out) < n and tries < 400:
        tries += 1
        num = rng.sample(names, rng.choice([1, 2, 2, 3]))
        den = rng.sample(names, rng.choice([1, 2, 2, 3]))
        dn, dd = sum(_BLOCKS[x][1] for x in num), sum(_BLOCKS[x][1] for x in den)
        if dn != dd or set(num) == set(den):
            continue
        expr = "*".join(_BLOCKS[x][0] for x in num) + "/(" + "*".join(_BLOCKS[x][0] for x in den) + ")"
        E = sp.sympify(expr, locals=_SYM)
        f = sp.lambdify((a, b, c), E, "numpy")
        pts = np.exp(np.random.default_rng(tries).uniform(-3, 3, (3, 3000)))
        m = float(E.subs({a: 1, b: 1, c: 1}))
        with np.errstate(all="ignore"):
            v = f(*pts)
        if np.all(v >= m - 1e-12):
            out.append(expr)
        elif np.all(v <= m + 1e-12):                       # maximised at a=b=c: use the reciprocal
            out.append("(" + "*".join(_BLOCKS[x][0] for x in den) + ")/(" + "*".join(_BLOCKS[x][0] for x in num) + ")")
    return out


# ---------------------------------------------------------------- one round
def run_round(st: dict, reg: Registry, use_llm: bool, echo=print, max_pairs: int = 12) -> list[dict]:
    st["rounds"] += 1
    log(f"round {st['rounds']}: proposing expressions ({'Qwen3-14B + structural' if use_llm else 'structural'})", echo)
    proposals = (propose_llm(st, echo=echo) if use_llm else []) + propose_structural(st, n=3 if use_llm else 6)
    new = {}
    for p in proposals:
        E, why = validate(p, {**st["expressions"], **new})
        if E is None:
            st["rejected"].append({"expr": p[:120], "why": why})
            echo(f"    rejected: {p[:70]}  [{why}]")
        else:
            name = f"E{len(st['expressions']) + len(new) + 1}"
            new[name] = str(E)
            echo(f"    accepted {name}: {E}")
    found = []
    pairs = [(pn, qn) for pn in new for qn in list(st["expressions"]) + list(new) if pn != qn]
    pairs += [(qn, pn) for pn in new for qn in st["expressions"]]
    random.Random(st["rounds"]).shuffle(pairs)
    allx = {**st["expressions"], **new}
    for pn, qn in pairs[:max_pairs]:
        key = f"{allx[pn]} || {allx[qn]}"
        if key in st["pairs_tried"]:
            continue
        st["pairs_tried"].append(key)
        P, Q = sp.sympify(allx[pn], locals=_SYM), sp.sympify(allx[qn], locals=_SYM)
        mP, mQ = theorems._min_value(P), theorems._min_value(Q)
        try:
            inf, _ = theorems.ratio_inf(P, Q, mP, mQ, starts=30)
        except Exception:
            continue
        if not (0.02 < inf < 50):
            continue
        k = theorems.snap(inf)
        if k is None:
            continue
        payload = {"P": str(P), "Q": str(Q), "k": str(k)}
        stmt = f"For all a,b,c > 0:  [{P}] − {mP}  ≥  {k} · ([{Q}] − {mQ})"
        cid = reg.add("inequality", stmt, payload, source=f"discover_loop round {st['rounds']}")
        status = gate.check(reg, cid, log=lambda *x: None)
        cl = reg.get(cid)
        sharp = isinstance(cl.get("evidence"), dict) and cl["evidence"].get("sharp")
        echo(f"    {status:16s} k = {k}{' (sharp)' if sharp else ''}:  [{pn}] vs [{qn}]")
        if status == "proved" and sharp:
            tight = theorems.prove(P, Q, mP, mQ, k * (1 + sp.Rational(1, 10 ** 6)), timeout_ms=30000) == "refuted"
            chain = implied_by_registry(reg, payload, cid)
            if not tight:
                echo(f"      not a discovery: constant not sharp to 1e-6 (k* is probably irrational near {k})")
                continue
            if chain:
                reg.set_novelty(cid, f"follows from proved registry inequalities: {chain}")
                echo(f"      not a discovery: {chain}")
                continue
            known_cls = theorems.CLASSICAL.get(_lib_name(allx[pn])) and theorems.CLASSICAL.get(_lib_name(allx[qn]))
            reg.set_novelty(cid, "known (very likely: both sides classical)" if known_cls else NOVELTY)
            if not known_cls:
                rec = {"claim": cid, "statement": stmt, "k": str(k), "round": st["rounds"]}
                st["discoveries"].append(rec)
                found.append(rec)
                log(f"DISCOVERY (proved, sharp, not known to Euresis): {stmt}  [{cid}]", echo)
    st["expressions"].update(new)
    return found


def _norm(e: str) -> str:
    return str(sp.sympify(e, locals=_SYM))


def implied_by_registry(reg: Registry, payload: dict, cid: str) -> str:
    """Is P − mP ≥ k(Q − mQ) a consequence of already-proved inequalities (direct or a two-step chain)?"""
    edges = {}
    for c in reg.claims(status="proved", kind="inequality"):
        if c["id"] == cid:
            continue
        p = c["payload"]
        try:
            key = (_norm(p["P"]), _norm(p["Q"]))
        except Exception:
            continue
        edges[key] = max(edges.get(key, sp.Rational(0)), sp.Rational(p["k"]))
    P, Q, k = _norm(payload["P"]), _norm(payload["Q"]), sp.Rational(payload["k"])
    if edges.get((P, Q), 0) >= k:
        return f"a proved inequality between the same expressions already has constant {edges[(P, Q)]}"
    for (x, y), k1 in edges.items():
        if x == P and (y, Q) in edges and k1 * edges[(y, Q)] >= k:
            return f"chain through {y[:60]} gives {k1}·{edges[(y, Q)]} ≥ {k}"
    return ""


def _lib_name(expr_str: str) -> str | None:
    for k, v in theorems.LIBRARY.items():
        if str(v) == expr_str:
            return k
    return None


# ------------------------------------------------------------------- loop
def run(minutes: float = 100.0, use_llm: bool | None = None, echo=print) -> dict:
    from . import local_llm
    if use_llm is None:
        use_llm = local_llm.available()
    st, reg = load_state(), Registry()
    t0 = time.time()
    log(f"segment start (budget {minutes:.0f} min; model: {'Qwen3-14B' if use_llm else 'none'}; "
        f"{len(st['discoveries'])} discoveries so far)", echo)
    while time.time() - t0 < minutes * 60:
        if STOP.exists():
            log("STOP file found — stopping as instructed", echo)
            break
        try:
            run_round(st, reg, use_llm, echo=echo)
        except Exception as e:                     # one bad round must not end the search
            log(f"round failed: {type(e).__name__}: {e}", echo)
        save_state(st)
    st["seconds"] = st.get("seconds", 0.0) + (time.time() - t0)
    save_state(st)
    log(f"segment end: {st['rounds']} rounds total, {len(st['discoveries'])} discoveries", echo)
    return st
