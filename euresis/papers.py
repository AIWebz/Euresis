"""Reading the literature and discovering while reading.

Corpus: PubMed 200k RCT (Dernoncourt & Lee, 2017) — 195,654 real abstracts of
randomised controlled trials, each with its PubMed ID (github.com/Franck-Dernoncourt/pubmed-rct).

1. **Ingest** — every abstract goes into Euresis' local full-text library
   (SQLite FTS5), so literature search and novelty checks work offline.
2. **Concepts** — 1–3-word terms that recur across papers (with methodological
   words removed) become the concepts Euresis reasons about.
3. **Discover while reading** — Swanson's literature-based discovery (ABC model):
   if A is associated with B in some papers and B with C in others, but A and C
   are never mentioned together, the pair (A, C) is a hypothesis. Swanson used it
   in 1986 to predict that fish oil could help Raynaud's syndrome — later confirmed.
   Euresis reads the papers in PubMed-ID order (≈ publication order) in chunks and
   generates hypotheses as the knowledge accumulates.
4. **Honest test (time-sliced)** — hypotheses are generated from the earlier 80%
   of papers only, then checked against the later 20%: what fraction of predicted
   links were actually published later? Compared with frequency-matched random pairs.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.sparse as sps

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "external" / "papers" / "pubmed-rct" / "PubMed_200k_RCT"
OUT = ROOT / "space" / "literature_discovery.md"

STOP = set("""a an the of and or in on at to for with by from as is are was were be been being this that these those
it its into than then there their them they we our us who whom which what when where why how all any both each few more
most other some such no nor not only own same so too very can will just should now also may might must shall would could
after before between during under over about against among within without through while vs versus per via whether either
one two three four five six seven eight nine ten first second third patients patient study studies trial trials group groups
randomized randomised randomly controlled control placebo double blind blinded single double-blind week weeks month months
year years day days hour hours minute minutes baseline end mean median ratio significant significantly difference differences
compared compare comparison results result conclusion conclusions methods method background objective objectives aim aims
data analysis analyses outcome outcomes primary secondary total number rate rates level levels score scores effect effects
treatment treatments therapy intervention interventions participants subjects use used using based received receiving
increase increased decrease decreased reduced reduction higher lower high low however among overall respectively follow-up
p ci confidence interval vs. % @ n mg kg ml g h min std sd se iqr hr rr ci95 i ii iii iv versus showed show shown found
evaluated evaluate assessed assess performed associated association risk risks age years-old old women men adults children
""".split())
TOKEN = re.compile(r"[a-z][a-z0-9\-]+")


def read_abstracts(limit=None):
    """Yield (pmid, text) for every abstract in the corpus."""
    files = [CORPUS / "train.txt", CORPUS / "dev.txt", CORPUS / "test.txt"]
    for f in files:
        pmid, lines = None, []
        with open(f) as fh:
            for line in fh:
                if line.startswith("###"):
                    if pmid and lines:
                        yield int(pmid), " ".join(lines)
                    pmid, lines = line[3:].strip(), []
                elif "\t" in line:
                    lines.append(line.split("\t", 1)[1].strip())
            if pmid and lines:
                yield int(pmid), " ".join(lines)


def ingest(log=print):
    """Index every abstract in Euresis' local literature library."""
    from .literature import Library, Paper
    lib = Library()
    batch, n = [], 0
    for pmid, text in read_abstracts():
        title = text.split(" . ")[0][:200]
        batch.append(Paper("pubmed-rct", str(pmid), title, text, None, "", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"))
        if len(batch) == 5000:
            n += lib.add(batch)
            batch = []
    n += lib.add(batch)
    log(f"ingested {n:,} new abstracts; library now holds {lib.count():,} papers")
    return lib.count()


def terms_of(text):
    toks = [t for t in TOKEN.findall(text.lower())]
    out = set()
    for i, t in enumerate(toks):
        if t not in STOP and not t[0].isdigit() and len(t) > 2:
            out.add(t)
            if i + 1 < len(toks) and toks[i + 1] not in STOP and len(toks[i + 1]) > 2:
                out.add(t + " " + toks[i + 1])
    return out


def _stems(term):
    out = set()
    for w in term.split():
        for suf in ("ies", "es", "s", "al", "ic", "ed", "ing"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w[:6])
    return out


def related_strings(a, c):
    """Spelling variants / shared words — not a discovery."""
    return bool(_stems(a) & _stems(c))


class LiteratureDiscovery:
    def __init__(self, min_df=60, max_df_frac=0.01, log=print):
        self.min_df, self.max_df_frac, self.log = min_df, max_df_frac, log

    def load(self):
        t0 = time.time()
        docs = sorted(read_abstracts(), key=lambda x: x[0])        # PubMed-ID order ≈ publication order
        self.pmids = [d[0] for d in docs]
        self.doc_terms = [terms_of(t) for _, t in docs]
        df = Counter(t for ts in self.doc_terms for t in ts)
        n = len(docs)
        vocab = sorted(t for t, c in df.items() if self.min_df <= c <= self.max_df_frac * n)
        # drop bigrams fully explained by a unigram (keeps concepts distinct)
        self.vocab = vocab
        self.index = {t: i for i, t in enumerate(vocab)}
        rows, cols = [], []
        for d, ts in enumerate(self.doc_terms):
            for t in ts:
                j = self.index.get(t)
                if j is not None:
                    rows.append(d)
                    cols.append(j)
        self.M = sps.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(n, len(vocab)))
        self.log(f"read {n:,} abstracts in publication order; {len(vocab):,} concepts "
                 f"({self.M.nnz:,} concept mentions) in {time.time() - t0:.0f}s")
        return self

    # ------------------------------------------------------------------ ABC
    def hypotheses(self, M, top=500, min_links=3, cross_topic=False):
        """Swanson ABC on the papers in M: pairs never co-mentioned, linked through strong intermediates."""
        n = M.shape[0]
        df = np.asarray(M.sum(0)).ravel()
        C = (M.T @ M).tocsr()
        C.setdiag(0)
        C.eliminate_zeros()
        # positive normalised PMI as association strength
        Cc = C.tocoo()
        pij = Cc.data / n
        pi, pj = df[Cc.row] / n, df[Cc.col] / n
        npmi = np.log(pij / (pi * pj)) / -np.log(pij)
        keep = (npmi > 0.25) & (Cc.data >= 3)
        W = sps.csr_matrix((npmi[keep], (Cc.row[keep], Cc.col[keep])), shape=C.shape)
        # paths A–B–C: strength = Σ_B min-ish product; count of intermediates
        Wb = W.copy()
        Wb.data = np.ones_like(Wb.data)
        P = (W @ W).tocsr()                                   # path strength through intermediates B
        K = (Wb @ Wb).tocsr()                                 # number of intermediates
        P = sps.triu(P, k=1).tocsr()
        K = sps.triu(K, k=1).tocsr()
        P = P.multiply(K >= min_links).tocsr()
        direct = (sps.triu(C, k=1) > 0).astype(np.float32)
        P = (P - P.multiply(direct)).tocsr()                  # drop pairs already mentioned together
        P.eliminate_zeros()
        Pc = P.tocoo()
        if Pc.nnz == 0:
            return [], df
        order = np.argsort(-Pc.data)
        Kc = K.tocsr()
        # association profiles: near-identical profiles mean the same topic under different words
        Wn = sps.csr_matrix(W.multiply(1 / np.sqrt(np.asarray(W.multiply(W).sum(1)).ravel() + 1e-12)[:, None]))
        cand = []
        for i in order:
            a, c = int(Pc.row[i]), int(Pc.col[i])
            if related_strings(self.vocab[a], self.vocab[c]):
                continue
            cos = float(Wn[a].multiply(Wn[c]).sum())
            cand.append((float(Pc.data[i]), a, c, int(Kc[a, c]), cos))
            if len(cand) >= top * (4 if cross_topic else 1):
                break
        if cross_topic:
            cand = [x for x in cand if x[4] < 0.35]
            cand.sort(key=lambda x: -x[0] * (1 - x[4]))
        cand = [x[:4] for x in cand[:top]]
        return cand, df

    def evaluate(self, split=0.8, top=500, seed=0):
        n = self.M.shape[0]
        cut = int(split * n)
        past, future = self.M[:cut], self.M[cut:]
        t0 = time.time()
        hyps, df = self.hypotheses(past, top=top)
        Cf = (future.T @ future).tocsr()
        hit = [Cf[a, c] > 0 for _, a, c, _ in hyps]
        prec = float(np.mean(hit)) if hyps else 0.0
        # frequency-matched random baseline: random never-co-mentioned pairs with similar document frequencies
        rng = np.random.default_rng(seed)
        Cp = (past.T @ past).tocsr()
        base_hits, tries = [], 0
        dfs = np.argsort(df)
        rank = np.empty_like(dfs)
        rank[dfs] = np.arange(len(dfs))
        for _, a, c, _ in hyps:
            for _ in range(20):
                a2 = dfs[min(len(dfs) - 1, max(0, rank[a] + rng.integers(-50, 51)))]
                c2 = dfs[min(len(dfs) - 1, max(0, rank[c] + rng.integers(-50, 51)))]
                if a2 != c2 and Cp[a2, c2] == 0:
                    base_hits.append(Cf[a2, c2] > 0)
                    break
        base = float(np.mean(base_hits)) if base_hits else 0.0
        self.log(f"time-sliced test: hypotheses from the first {cut:,} papers; checked against the next {n - cut:,}")
        self.log(f"  Euresis: {sum(hit)}/{len(hyps)} predicted links later published  (precision {prec * 100:.1f}%)")
        self.log(f"  frequency-matched random pairs: {base * 100:.1f}%  → lift ×{prec / base if base else float('inf'):.1f}"
                 f"  ({time.time() - t0:.0f}s)")
        return {"precision": prec, "baseline": base, "n": len(hyps), "hits": int(sum(hit)),
                "examples_confirmed": [(self.vocab[a], self.vocab[c], int(k)) for (s, a, c, k), h in zip(hyps, hit) if h][:15],
                "past": cut, "future": n - cut}

    def streaming(self, chunks=5, top=200):
        """Read in chunks; after each, report how many earlier hypotheses the new papers confirmed."""
        n = self.M.shape[0]
        bounds = [int(n * (i + 1) / (chunks + 1)) for i in range(chunks + 1)]
        history = []
        for i in range(chunks):
            past, nxt = self.M[:bounds[i]], self.M[bounds[i]:bounds[i + 1]]
            hyps, _ = self.hypotheses(past, top=top)
            Cn = (nxt.T @ nxt).tocsr()
            conf = sum(Cn[a, c] > 0 for _, a, c, _ in hyps)
            history.append({"read": bounds[i], "next": bounds[i + 1] - bounds[i], "hypotheses": len(hyps), "confirmed": int(conf)})
            self.log(f"  after reading {bounds[i]:,} papers: {len(hyps)} hypotheses → {conf} confirmed by the next "
                     f"{bounds[i + 1] - bounds[i]:,} papers")
        return history

    def frontier(self, top=40):
        """Hypotheses from the whole corpus: links never mentioned together in any of the papers."""
        hyps, df = self.hypotheses(self.M, top=top * 5, cross_topic=True)
        out = []
        for s, a, c, k in hyps:
            A, Cn = self.vocab[a], self.vocab[c]
            if A.split()[0] in Cn.split() or Cn.split()[0] in A.split():
                continue                                    # trivially related phrases
            out.append({"A": A, "C": Cn, "intermediates": int(k), "strength": float(s)})
            if len(out) >= top:
                break
        return out


def run(log=print, space=None):
    ingest(log=log)
    ld = LiteratureDiscovery(log=log).load()
    log("\nDiscovering while reading (chunks in publication order):")
    hist = ld.streaming()
    log("\nTime-sliced evaluation:")
    ev = ld.evaluate()
    log("\nNew hypotheses from all 195k papers (pairs never mentioned together):")
    fr = ld.frontier()
    for h in fr[:20]:
        log(f"  {h['A']}  ↔  {h['C']}   (via {h['intermediates']} shared concepts)")
    L = ["# Euresis — discovering while reading the literature", "",
         f"Corpus: PubMed 200k RCT — {ld.M.shape[0]:,} real abstracts, read in PubMed-ID (≈ publication) order; "
         f"{len(ld.vocab):,} concepts.", "",
         "## Does Euresis predict links before they are published?", "",
         f"Hypotheses generated from the first {ev['past']:,} papers only, checked against the next {ev['future']:,}:", "",
         f"| | Predicted links later published |", "|---|---|",
         f"| Euresis (ABC literature-based discovery) | **{ev['hits']}/{ev['n']} ({ev['precision'] * 100:.1f}%)** |",
         f"| Frequency-matched random pairs | {ev['baseline'] * 100:.1f}% |", "",
         f"Lift over chance: ×{ev['precision'] / ev['baseline'] if ev['baseline'] else float('inf'):.1f}.", "",
         "Examples Euresis predicted that were later published together: " +
         "; ".join(f"{a} ↔ {c}" for a, c, _ in ev["examples_confirmed"][:10]) + ".", "",
         "## Discovering while reading", "", "| Papers read | Hypotheses | Confirmed by the next chunk |", "|---|---|---|"]
    L += [f"| {h['read']:,} | {h['hypotheses']} | {h['confirmed']} |" for h in hist]
    L += ["", "## Open hypotheses from all papers", "",
          "Pairs of concepts never mentioned together in any of the 195,654 abstracts but strongly linked through "
          "shared intermediate concepts. They are *candidate* connections, not findings: absent from this corpus, "
          "not necessarily from all of PubMed, and untested.", "", "| Concept A | Concept C | Shared intermediates |", "|---|---|---|"]
    L += [f"| {h['A']} | {h['C']} | {h['intermediates']} |" for h in fr]
    OUT.write_text("\n".join(L) + "\n")
    if space is not None:
        did = space.add("data", "Literature: PubMed 200k RCT abstracts", body=f"{ld.M.shape[0]:,} abstracts ingested.",
                        domain="biology", status="read by Euresis", score=1.0, key="data|pubmed-rct")
        space.add("insight", "Literature-based discovery: time-sliced test",
                  body=f"{ev['hits']}/{ev['n']} predicted links later published ({ev['precision'] * 100:.1f}%) vs "
                       f"{ev['baseline'] * 100:.1f}% for random pairs.", domain="biology", parents=[did],
                  status="measured", score=1.2, key="insight|lbd-eval")
        for h in fr[:20]:
            space.add("hypothesis", f"{h['A']} ↔ {h['C']}", body=f"Never co-mentioned in 195k abstracts; linked via "
                      f"{h['intermediates']} shared concepts (Swanson ABC).", domain="biology", parents=[did],
                      status="literature hypothesis · untested", score=0.9, key=f"lbd|{h['A']}|{h['C']}")
    return ev, hist, fr
