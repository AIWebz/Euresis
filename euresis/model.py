"""The trainable part of Euresis.

Two learned components, trained from scratch on the knowledge base:

* ``ConceptEmbedding`` — a link-prediction model. Every quantity and constant
  becomes a vector; vectors are trained (logistic matrix factorisation with
  negative sampling, plain NumPy SGD) so that concepts appearing together in a
  law of nature score high. It is used to *guess* which concepts ought to be
  related even where no known formula connects them — the starting point for
  new hypotheses.
* ``TextRetriever`` — latent semantic analysis (TF-IDF + truncated SVD) over the
  whole corpus, used to retrieve relevant knowledge for a question.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from .kb import KnowledgeBase, family

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


def _formula_nodes(f) -> list[str]:
    nodes = {f"q:{family(q)}" for q in f.quantities} | {f"q:{q}" for q in f.quantities}
    nodes |= {f"c:{c.name}" for c in f.constants}
    nodes.add(f"d:{f.domain}")
    return sorted(nodes)


class ConceptEmbedding:
    def __init__(self, nodes: list[str], dim: int = 32, seed: int = 7):
        self.nodes = nodes
        self.index = {n: i for i, n in enumerate(nodes)}
        rng = np.random.default_rng(seed)
        self.W = rng.normal(0, 0.1, (len(nodes), dim))
        self.b = np.zeros(len(nodes))
        self.history: list[float] = []

    # -------------------------------------------------------------- training
    @staticmethod
    def edges_from(kb: KnowledgeBase) -> set[tuple[str, str]]:
        edges = set()
        for f in kb.formulas:
            for a, b in combinations(_formula_nodes(f), 2):
                edges.add((a, b))
        return edges

    def fit(self, edges, epochs=400, lr=0.05, neg=5, l2=1e-4, seed=0):
        rng = np.random.default_rng(seed)
        E = np.array([[self.index[a], self.index[b]] for a, b in edges])
        n = len(self.nodes)
        for ep in range(epochs):
            rng.shuffle(E)
            negs = rng.integers(0, n, (len(E), neg))
            src = np.concatenate([E[:, 0], np.repeat(E[:, 0], neg)])
            dst = np.concatenate([E[:, 1], negs.ravel()])
            y = np.concatenate([np.ones(len(E)), np.zeros(len(E) * neg)])
            s = np.sum(self.W[src] * self.W[dst], 1) + self.b[src] + self.b[dst]
            p = 1 / (1 + np.exp(-s))
            loss = -np.mean(y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9))
            g = (p - y)[:, None]
            gW = np.zeros_like(self.W)
            np.add.at(gW, src, g * self.W[dst])
            np.add.at(gW, dst, g * self.W[src])
            gb = np.zeros_like(self.b)
            np.add.at(gb, src, g[:, 0])
            np.add.at(gb, dst, g[:, 0])
            cnt = np.bincount(np.concatenate([src, dst]), minlength=n)[:, None] + 1
            self.W -= lr * (gW / np.sqrt(cnt) + l2 * self.W) * 10
            self.b -= lr * gb / cnt[:, 0] * 10
            self.history.append(float(loss))
        return self

    # ------------------------------------------------------------- inference
    def score(self, a: str, b: str) -> float:
        if a not in self.index or b not in self.index:
            return 0.0
        i, j = self.index[a], self.index[b]
        return float(1 / (1 + math.exp(-(self.W[i] @ self.W[j] + self.b[i] + self.b[j]))))

    def similar(self, a: str, k=10, prefix="q:") -> list[tuple[str, float]]:
        i = self.index[a]
        v = self.W / (np.linalg.norm(self.W, axis=1, keepdims=True) + 1e-9)
        sims = v @ v[i]
        order = np.argsort(-sims)
        return [(self.nodes[j], float(sims[j])) for j in order
                if j != i and self.nodes[j].startswith(prefix)][:k]

    def related(self, a: str, k=10, prefix=("q:", "c:")) -> list[tuple[str, float]]:
        out = [(n, self.score(a, n)) for n in self.nodes if n != a and n.startswith(prefix)]
        return sorted(out, key=lambda t: -t[1])[:k]

    def auc(self, pos, neg) -> float:
        sp = np.array([self.score(a, b) for a, b in pos])
        sn = np.array([self.score(a, b) for a, b in neg])
        return float((sp[:, None] > sn[None, :]).mean() + 0.5 * (sp[:, None] == sn[None, :]).mean())

    def save(self, path: Path):
        np.savez(path, W=self.W, b=self.b, nodes=np.array(self.nodes))

    @classmethod
    def load(cls, path: Path) -> "ConceptEmbedding":
        z = np.load(path, allow_pickle=False)
        m = cls(list(z["nodes"]), dim=z["W"].shape[1])
        m.W, m.b = z["W"], z["b"]
        return m


class TextRetriever:
    TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9]+")
    STOP = set("the of and a an to in is for by on with as at from that this be are or it its into".split())

    def __init__(self, docs: list[tuple[str, str, str]], k: int = 96):
        self.docs = docs
        toks = [self._tok(d[2]) for d in docs]
        df = Counter(t for ts in toks for t in set(ts))
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        N = len(docs)
        self.idf = np.array([math.log((1 + N) / (1 + df[t])) + 1 for t in sorted(df)])
        X = np.zeros((N, len(self.vocab)))
        for i, ts in enumerate(toks):
            for t, c in Counter(ts).items():
                X[i, self.vocab[t]] = (1 + math.log(c)) * self.idf[self.vocab[t]]
        X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
        U, S, Vt = np.linalg.svd(X, full_matrices=False)
        k = min(k, len(S))
        self.Vt = Vt[:k]
        self.D = X @ self.Vt.T
        self.D /= np.linalg.norm(self.D, axis=1, keepdims=True) + 1e-9
        self.X = X

    def _tok(self, s):
        return [t.lower() for t in self.TOKEN.findall(s) if t.lower() not in self.STOP]

    def _vec(self, q):
        v = np.zeros(len(self.vocab))
        for t, c in Counter(self._tok(q)).items():
            if t in self.vocab:
                v[self.vocab[t]] = (1 + math.log(c)) * self.idf[self.vocab[t]]
        return v / (np.linalg.norm(v) + 1e-9)

    def search(self, query: str, k: int = 8):
        v = self._vec(query)
        lsa = self.D @ (self.Vt @ v)
        lex = self.X @ v
        s = 0.5 * lsa + 0.5 * lex
        order = np.argsort(-s)[:k]
        return [(self.docs[i], float(s[i])) for i in order]


def train(kb: KnowledgeBase, out_dir: Path = MODEL_DIR, epochs=400, seed=0, verbose=True) -> dict:
    """Train the concept embedding and report held-out link-prediction AUC."""
    out_dir.mkdir(parents=True, exist_ok=True)
    edges = sorted(ConceptEmbedding.edges_from(kb))
    nodes = sorted({n for e in edges for n in e})
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(edges))
    n_test = len(edges) // 10
    test = [edges[i] for i in idx[:n_test]]
    trainset = [edges[i] for i in idx[n_test:]]
    eset = set(edges) | {(b, a) for a, b in edges}
    negs = []
    while len(negs) < len(test):
        a, b = nodes[rng.integers(len(nodes))], nodes[rng.integers(len(nodes))]
        if a != b and (a, b) not in eset:
            negs.append((a, b))
    # 1) evaluation run on a 90/10 split
    m = ConceptEmbedding(nodes).fit(trainset, epochs=epochs, seed=seed)
    auc = m.auc(test, negs)
    # 2) final model on all edges
    final = ConceptEmbedding(nodes).fit(edges, epochs=epochs, seed=seed)
    final.save(out_dir / "euresis-concepts.npz")
    metrics = {"nodes": len(nodes), "edges": len(edges), "epochs": epochs,
               "final_loss": final.history[-1], "initial_loss": final.history[0],
               "heldout_link_auc": auc, "loss_curve": final.history[:: max(1, epochs // 40)]}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    if verbose:
        print(f"trained concept embedding: {len(nodes)} concepts, {len(edges)} relations")
        print(f"loss {metrics['initial_loss']:.3f} -> {metrics['final_loss']:.3f}; "
              f"held-out link-prediction AUC = {auc:.3f}")
    return metrics


def load_or_train(kb: KnowledgeBase) -> ConceptEmbedding:
    p = MODEL_DIR / "euresis-concepts.npz"
    if not p.exists():
        train(kb, verbose=False)
    m = ConceptEmbedding.load(p)
    return m
