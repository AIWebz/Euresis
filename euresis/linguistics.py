"""Linguistics discovery: statistical laws of written language, found on one corpus and
confirmed on a separate, held-out one.

Corpus: PubMed RCT abstracts (real medical writing, numbers replaced by '@').
Discovery half = the dev split; confirmation half = the test split (different abstracts).

Euresis measures features of every sentence (length in words, mean word length,
share of long words, commas, parentheses, numbers, function-word share, mean word
frequency, position in the abstract) and of every word type (length, syllables,
log frequency, number of distinct neighbours). It searches for monotone relations
between pairs of features (Spearman ρ) and partial relations with sentence length held
fixed. A relation counts only if it is strong (|ρ| ≥ 0.15) and significant
(p < 1e-6 after Bonferroni) in the discovery half AND confirmed with the same sign,
|ρ| ≥ 0.1 and p < 1e-6 in the held-out half. The verification gate (claim kind
``empirical``) re-runs the test on the held-out corpus independently.

These are empirical findings about one genre of text — evidence, not proof — and
known laws (Zipf, Menzerath–Altmann, …) are reported as rediscoveries.
"""
from __future__ import annotations

import itertools
import json
import math
import re
import time
from collections import Counter
from functools import lru_cache

import numpy as np
from scipy import stats

from .registry import ROOT, Registry

CORPUS = ROOT / "data" / "external" / "papers" / "pubmed-rct" / "PubMed_200k_RCT_numbers_replaced_with_at_sign"
STATE = ROOT / "space" / "linguistics_state.json"
LOG = ROOT / "space" / "linguistics_log.md"

FUNCTION_WORDS = set("the a an of in on at to for with by from and or but as is are was were be been that this "
                     "these those which who it its than not no".split())
WORD = re.compile(r"[a-z]+(?:-[a-z]+)*")


@lru_cache(maxsize=None)
def load(split: str):
    """→ list of abstracts, each a list of (section, sentence)."""
    out, cur = [], None
    with open(CORPUS / f"{split}.txt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("###"):
                cur = []
                out.append(cur)
            elif line and cur is not None and "\t" in line:
                sec, text = line.split("\t", 1)
                cur.append((sec, text))
    return out


def _syllables(w: str) -> int:
    return max(1, len(re.findall(r"[aeiouy]+", w)))


@lru_cache(maxsize=None)
def word_freq(split: str) -> Counter:
    c = Counter()
    for ab in load(split):
        for _, s in ab:
            c.update(WORD.findall(s.lower()))
    return c


SENT_FEATURES = ("number of words", "mean word length", "share of long words (≥ 7 letters)", "number of commas",
                 "number of parentheses", "number of numbers", "share of function words",
                 "mean log frequency of its words", "relative position in the abstract")
WORD_FEATURES = ("word length", "syllables", "log frequency", "number of distinct following words")

DEFINITIONAL = {frozenset(p) for p in [
    ("mean word length", "share of long words (≥ 7 letters)"), ("word length", "syllables"),
    ("share of function words", "mean log frequency of its words"),
    ("mean word length", "mean log frequency of its words"), ("mean word length", "share of function words"),
    ("share of long words (≥ 7 letters)", "share of function words"),
    ("share of long words (≥ 7 letters)", "mean log frequency of its words"),
    ("log frequency", "number of distinct following words")]}

KNOWN = {
    frozenset(("word length", "log frequency")): "Zipf's law of abbreviation (frequent words are shorter)",
    frozenset(("syllables", "log frequency")): "Zipf's law of abbreviation (frequent words are shorter)",
    frozenset(("number of words", "mean word length")): "Menzerath–Altmann law (longer constructs, shorter parts)",
    frozenset(("number of words", "number of commas")): "longer sentences have more clauses (elementary)",
    frozenset(("number of words", "number of parentheses")): "elementary length effect",
    frozenset(("number of words", "number of numbers")): "elementary length effect",
    frozenset(("number of words", "share of long words (≥ 7 letters)")): "Menzerath–Altmann law (longer constructs, shorter parts)",
    frozenset(("number of parentheses", "number of numbers")): "genre convention: statistics are reported in parentheses, e.g. (n = @)",
}
# "share of long words" measures the same thing as "mean word length": test it only where mean word length is not
REDUNDANT = {"share of long words (≥ 7 letters)": "mean word length"}


@lru_cache(maxsize=None)
def sentence_table(split: str) -> np.ndarray:
    freq = word_freq("dev")                       # frequencies always from the discovery half
    rows = []
    for ab in load(split):
        n = len(ab)
        for i, (_, s) in enumerate(ab):
            toks = s.split()
            words = WORD.findall(s.lower())
            if len(words) < 3:
                continue
            lens = [len(w) for w in words]
            rows.append([len(toks), float(np.mean(lens)), float(np.mean([l >= 7 for l in lens])), s.count(","),
                         s.count("("), s.count("@"), float(np.mean([w in FUNCTION_WORDS for w in words])),
                         float(np.mean([math.log(freq.get(w, 0) + 1) for w in words])),
                         i / max(1, n - 1)])
    return np.array(rows, float)


@lru_cache(maxsize=None)
def word_table(split: str) -> np.ndarray:
    freq = word_freq(split)
    nxt = {}
    for ab in load(split):
        for _, s in ab:
            ws = WORD.findall(s.lower())
            for a, b in zip(ws, ws[1:]):
                nxt.setdefault(a, set()).add(b)
    rows = [[len(w), _syllables(w), math.log(c), len(nxt.get(w, ()))] for w, c in freq.items() if c >= 3]
    return np.array(rows, float)


def _partial(x, y, z):
    """Spearman partial correlation of x and y given z."""
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))
    def resid(a, b):
        A = np.stack([np.ones_like(b), b], 1)
        coef, *_ = np.linalg.lstsq(A, a, rcond=None)
        return a - A @ coef
    return stats.pearsonr(resid(rx, rz), resid(ry, rz))


def test(unit: str, fx: str, fy: str, split: str, control: bool) -> tuple[float, float]:
    names = SENT_FEATURES if unit == "sentence" else WORD_FEATURES
    T = sentence_table(split) if unit == "sentence" else word_table(split)
    x, y = T[:, names.index(fx)], T[:, names.index(fy)]
    if control:
        r, p = _partial(x, y, T[:, 0])
    else:
        r, p = stats.spearmanr(x, y)
    return float(r), float(p)


# ------------------------------------------------------------------ verifier (gate)
def verify_claim(p: dict) -> tuple[str, dict]:
    """Re-run the test on the held-out corpus."""
    r, pv = test(p["unit"], p["x"], p["y"], "test", p.get("control_length", False))
    ok = math.copysign(1, r) == p["sign"] and abs(r) >= 0.1 and pv < 1e-6
    ev = {"held_out_rho": round(r, 4), "held_out_p": pv, "corpus": "PubMed RCT test split (held out)",
          "note": "empirical confirmation on held-out data — evidence, not proof"}
    return ("verified-numeric" if ok else "refuted"), ev


# ---------------------------------------------------------------- discovery
def log(msg, echo=print):
    echo(msg)
    with LOG.open("a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


def run(reg: Registry | None = None, echo=print) -> dict:
    from . import gate
    reg = reg or Registry()
    st = {"discoveries": [], "rediscoveries": [], "tests": 0}
    log(f"linguistics: {sum(len(a) for a in load('dev'))} discovery sentences, "
        f"{sum(len(a) for a in load('test'))} held-out sentences", echo)
    hyps = [("sentence", a, b, False) for a, b in itertools.combinations(SENT_FEATURES, 2)]
    hyps += [("sentence", a, b, True) for a, b in itertools.combinations(SENT_FEATURES[1:], 2)]
    hyps += [("word", a, b, False) for a, b in itertools.combinations(WORD_FEATURES, 2)]
    bonf = 1e-6 / len(hyps)
    done = set()
    for unit, a, b, ctrl in hyps:
        if frozenset((a, b)) in DEFINITIONAL:
            continue
        key = (unit, frozenset(REDUNDANT.get(x, x) for x in (a, b)), ctrl)
        if key in done:
            continue                                   # same relation already tested with the equivalent feature
        done.add(key)
        st["tests"] += 1
        r, pv = test(unit, a, b, "dev", ctrl)
        if abs(r) < 0.15 or pv > bonf:
            continue
        direction = "more" if r > 0 else "less"
        cond = " (with sentence length held fixed)" if ctrl else ""
        stmt = (f"In medical research abstracts, {unit}s with a higher '{a}' have {direction} '{b}'{cond}: "
                f"Spearman ρ = {r:+.3f} (discovery half)")
        payload = {"unit": unit, "x": a, "y": b, "sign": 1 if r > 0 else -1, "control_length": ctrl}
        cid = reg.add("empirical", stmt, payload, source="linguistics.py")
        status = gate.check(reg, cid, log=lambda *x: None)
        ev = reg.get(cid)["evidence"]
        if status != "verified-numeric":
            echo(f"    not confirmed on held-out text: {stmt}  (held-out ρ = {ev.get('held_out_rho')})")
            continue
        why = KNOWN.get(frozenset((a, b))) if not ctrl else None
        if why:
            reg.set_novelty(cid, f"known ({why})")
            st["rediscoveries"].append({"claim": cid, "statement": stmt, "known": why})
            echo(f"    rediscovered: {stmt}  [{why}; held-out ρ = {ev['held_out_rho']:+.3f}]")
        else:
            reg.set_novelty(cid, "not among the linguistic laws Euresis knows; specific to medical abstracts; "
                                 "linguistics literature unchecked")
            rec = {"claim": cid, "statement": stmt, "held_out_rho": ev["held_out_rho"]}
            st["discoveries"].append(rec)
            log(f"FINDING (confirmed on held-out text, not proved): {stmt}; held-out ρ = {ev['held_out_rho']:+.3f} "
                f"[{cid}]", echo)
    atomic_write(STATE, json.dumps(st, indent=1) + "\n")
    return st
