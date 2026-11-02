"""The scientific literature: live search + a growing local full-text index.

Sources (public APIs, no key needed):
  * arXiv            — export.arxiv.org/api/query            (physics, maths, CS, q-bio …)
  * PubMed           — eutils.ncbi.nlm.nih.gov (esearch+efetch) (biomedicine, ~37M records)
  * Semantic Scholar — api.semanticscholar.org/graph/v1          (~200M papers, all fields)
  * OpenAlex         — api.openalex.org/works                     (~250M works, all fields)

Every paper fetched is stored in a local SQLite FTS5 index (``data/literature.db``)
so it can be searched offline and the index grows with use. ``harvest`` bulk-loads
papers on a topic; the index has no size limit beyond disk space.

``novelty`` answers the question Euresis could not answer before: is this idea
already published? It searches every reachable source plus the local index,
scores each abstract against the idea, and returns the closest prior work with
a verdict. "No close match" is reported as exactly that — absence of evidence
in the papers searched, never proof of novelty.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "literature.db"
UA = "Euresis/1.0 (scientific discovery engine; https://github.com/aiwebz/euresis)"
TIMEOUT = 20


@dataclass
class Paper:
    source: str
    id: str
    title: str
    abstract: str
    year: int | None
    authors: str
    url: str
    doi: str = ""

    @property
    def key(self) -> str:
        return (self.doi or f"{self.source}:{self.id}").lower()


class SourceUnavailable(Exception):
    pass


def _get(url: str, accept="application/json") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except Exception as e:  # network policy, DNS, HTTP errors, timeouts
        raise SourceUnavailable(f"{urllib.parse.urlparse(url).netloc}: {e}") from e


# ------------------------------------------------------------------ sources
def search_arxiv(query: str, n=10) -> list[Paper]:
    q = urllib.parse.urlencode({"search_query": f"all:{query}", "start": 0, "max_results": n,
                                "sortBy": "relevance"})
    root = ET.fromstring(_get(f"http://export.arxiv.org/api/query?{q}", "application/atom+xml"))
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    out = []
    for e in root.findall("a:entry", ns):
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        year = (e.findtext("a:published", "", ns) or "")[:4]
        out.append(Paper("arxiv", aid, " ".join((e.findtext("a:title", "", ns) or "").split()),
                         " ".join((e.findtext("a:summary", "", ns) or "").split()),
                         int(year) if year.isdigit() else None,
                         ", ".join(a.findtext("a:name", "", ns) for a in e.findall("a:author", ns))[:300],
                         f"https://arxiv.org/abs/{aid}", e.findtext("arxiv:doi", "", ns) or ""))
    return out


def search_pubmed(query: str, n=10) -> list[Paper]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    ids = json.loads(_get(f"{base}/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": query, "retmax": n, "retmode": "json"})))["esearchresult"]["idlist"]
    if not ids:
        return []
    root = ET.fromstring(_get(f"{base}/efetch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}), "application/xml"))
    out = []
    for art in root.iter("PubmedArticle"):
        pmid = art.findtext(".//PMID", "")
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        abstract = " ".join("".join(t.itertext()) for t in art.iter("AbstractText"))
        year = art.findtext(".//PubDate/Year", "")
        authors = ", ".join(f"{a.findtext('ForeName', '')} {a.findtext('LastName', '')}".strip()
                            for a in art.iter("Author"))[:300]
        doi = next((i.text or "" for i in art.iter("ArticleId") if i.get("IdType") == "doi"), "")
        out.append(Paper("pubmed", pmid, title, abstract, int(year) if year.isdigit() else None, authors,
                         f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", doi))
    return out


def search_semantic_scholar(query: str, n=10) -> list[Paper]:
    q = urllib.parse.urlencode({"query": query, "limit": n,
                                "fields": "title,abstract,year,authors,externalIds,url"})
    data = json.loads(_get(f"https://api.semanticscholar.org/graph/v1/paper/search?{q}"))
    out = []
    for p in data.get("data", []):
        out.append(Paper("semanticscholar", p.get("paperId", ""), p.get("title") or "", p.get("abstract") or "",
                         p.get("year"), ", ".join(a.get("name", "") for a in p.get("authors", []))[:300],
                         p.get("url") or "", (p.get("externalIds") or {}).get("DOI", "") or ""))
    return out


def _openalex_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def search_openalex(query: str, n=10) -> list[Paper]:
    q = urllib.parse.urlencode({"search": query, "per-page": n, "mailto": "euresis@example.org"})
    data = json.loads(_get(f"https://api.openalex.org/works?{q}"))
    out = []
    for w in data.get("results", []):
        out.append(Paper("openalex", w.get("id", "").rsplit("/", 1)[-1], w.get("title") or "",
                         _openalex_abstract(w.get("abstract_inverted_index")), w.get("publication_year"),
                         ", ".join(a["author"]["display_name"] for a in w.get("authorships", [])
                                   if a.get("author"))[:300],
                         w.get("id", ""), (w.get("doi") or "").replace("https://doi.org/", "")))
    return out


SOURCES = {"arxiv": search_arxiv, "pubmed": search_pubmed, "semanticscholar": search_semantic_scholar,
           "openalex": search_openalex}


# --------------------------------------------------------------- local index
class Library:
    """Local full-text index of every paper Euresis has seen."""

    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS papers (key TEXT PRIMARY KEY, source TEXT, id TEXT, "
                        "title TEXT, abstract TEXT, year INT, authors TEXT, url TEXT, doi TEXT, added REAL)")
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(key UNINDEXED, title, abstract)")
        self.db.commit()

    def add(self, papers: list[Paper]) -> int:
        n = 0
        for p in papers:
            if not (p.title or p.abstract):
                continue
            cur = self.db.execute("INSERT OR IGNORE INTO papers VALUES (?,?,?,?,?,?,?,?,?,?)",
                                  (p.key, p.source, p.id, p.title, p.abstract, p.year, p.authors, p.url,
                                   p.doi, time.time()))
            if cur.rowcount:
                self.db.execute("INSERT INTO fts VALUES (?,?,?)", (p.key, p.title, p.abstract))
                n += 1
        self.db.commit()
        return n

    def search(self, query: str, n=20) -> list[Paper]:
        terms = [t for t in re.findall(r"[A-Za-z0-9]{3,}", query)]
        if not terms:
            return []
        match = " OR ".join(f'"{t}"' for t in terms)
        rows = self.db.execute(
            "SELECT p.source,p.id,p.title,p.abstract,p.year,p.authors,p.url,p.doi FROM fts "
            "JOIN papers p ON p.key = fts.key WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?", (match, n)).fetchall()
        return [Paper(*r) for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM papers").fetchone()[0]


# --------------------------------------------------------------- operations
def search(query: str, n=10, sources=None, library: Library | None = None, log=None):
    """Search every reachable source; store results; return (papers, status per source)."""
    lib = library or Library()
    papers, status = [], {}
    for name in sources or SOURCES:
        try:
            got = SOURCES[name](query, n)
            status[name] = f"ok ({len(got)})"
            papers += got
            lib.add(got)
        except SourceUnavailable as e:
            status[name] = f"unavailable: {e}"
        except (ValueError, KeyError, ET.ParseError) as e:
            status[name] = f"unexpected response: {e}"
    local = lib.search(query, n)
    status["local index"] = f"ok ({len(local)} of {lib.count()} indexed)"
    seen, out = set(), []
    for p in papers + local:
        if p.key not in seen:
            seen.add(p.key)
            out.append(p)
    if log:
        for k, v in status.items():
            log(f"  {k}: {v}")
    return out, status


def harvest(queries: list[str], per_query=100, sources=None, log=print) -> int:
    """Bulk-load papers on given topics into the local index."""
    lib = Library()
    before = lib.count()
    for q in queries:
        for name in sources or SOURCES:
            try:
                got = SOURCES[name](q, per_query)
                log(f"  {name} '{q}': +{lib.add(got)} papers")
            except SourceUnavailable as e:
                log(f"  {name}: unavailable ({e})")
    log(f"local index: {before} -> {lib.count()} papers")
    return lib.count() - before


_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")
_STOP = set("the and for with that this from are was were which these those into using use used based "
            "between their than then also can our its has have been not show shows study new".split())


def _vec(text: str) -> Counter:
    return Counter(t.lower() for t in _TOKEN.findall(text) if t.lower() not in _STOP)


def _cos(a: Counter, b: Counter) -> float:
    num = sum(a[t] * b[t] for t in a if t in b)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def novelty(statement: str, keywords: list[str] | None = None, n=15, log=None) -> dict:
    """Is an idea already in the literature? Returns verdict, closest papers and coverage."""
    query = " ".join((keywords or []) + [w for w in _TOKEN.findall(statement)][:12])
    papers, status = search(query, n, log=log)
    reachable = [k for k, v in status.items() if v.startswith("ok") and k != "local index"]
    iv = _vec(statement + " " + " ".join(keywords or []))
    scored = sorted(((round(_cos(iv, _vec(p.title + " " + p.abstract)), 3), p) for p in papers),
                    key=lambda x: -x[0])
    top = scored[:5]
    best = top[0][0] if top else 0.0
    if not reachable and not papers:
        verdict = "unchecked — no literature source reachable and the local index has no related papers"
    elif best >= 0.45:
        verdict = "likely already published — a closely matching paper was found"
    elif best >= 0.25:
        verdict = "related work exists — read the closest papers before claiming novelty"
    else:
        verdict = (f"no close match in {len(papers)} papers searched — not proof of novelty "
                   f"(searched: {', '.join(reachable) or 'local index only'})")
    return {"verdict": verdict, "best_similarity": best, "papers_searched": len(papers),
            "sources": status, "closest": [{"similarity": s, **asdict(p)} for s, p in top]}
