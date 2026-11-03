"""Evaluate Euresis-LM's language understanding: question → relevant law.

Two test sets, neither seen in training:
* **held-out phrasings** — questions generated with templates excluded from training;
* **natural questions** — everyday-language questions written by a person, each
  labelled with the law a scientist would point to.

Compared against Euresis' previous word-matching retriever (TF-IDF + LSA) and a
fusion of both.
"""
from __future__ import annotations

import random

import numpy as np

NATURAL = [
    ("How fast must a rocket go to leave Earth for good?", "Escape velocity"),
    ("Why does a longer pendulum swing more slowly?", "Simple pendulum period"),
    ("How long does a planet take to go around its star?", "Kepler's third law"),
    ("Why do objects float in water?", "Archimedes' principle"),
    ("How much energy is locked in a small amount of mass?", "Mass-energy equivalence"),
    ("Why do hot stars glow so brightly?", "Stefan-Boltzmann law"),
    ("Why does the colour of a hot object shift as it heats up?", "Wien's displacement law"),
    ("How does the pressure of a gas change when you squeeze it?", "Boyle's law (isothermal)"),
    ("How quickly does a radioactive sample lose half its atoms?", "Half-life"),
    ("Why do reactions speed up when it gets warmer?", "Arrhenius equation"),
    ("How fast does a bacterial colony grow when food is unlimited?", "Exponential population growth"),
    ("Why do moving clocks run slow?", "Time dilation"),
    ("How hot is a black hole?", "Hawking temperature of a black hole"),
    ("How much current flows through a resistor for a given voltage?", "Ohm's law"),
    ("How does light bend when it enters water?", "Snell's law"),
    ("Why does the pitch of a passing siren change?", "Doppler effect (moving source)"),
    ("How far does a thrown ball travel?", "Projectile range"),
    ("How strongly do two charges attract?", "Coulomb's law"),
    ("How fast does a small sphere sink through honey?", "Stokes terminal velocity"),
    ("How much does air pressure drop as you climb a mountain?", "Barometric formula"),
    ("What is the energy of a single photon of light?", "Planck-Einstein relation"),
    ("How quickly do enzymes work at different substrate levels?", "Michaelis-Menten kinetics"),
    ("Why do bigger animals have slower metabolisms per kilogram?", "Kleiber's law"),
    ("What fraction of people must be immune to stop an epidemic?", "Herd immunity threshold"),
]


def _rr(ranked, truth):
    for i, x in enumerate(ranked):
        if x == truth:
            return i
    return 10 ** 6


def evaluate(n_heldout=150, seed=0, log=print, model_dir=None):
    from ..kb import KnowledgeBase
    from ..model import TextRetriever
    from .corpus import build
    from .model import EuresisLM
    kb = KnowledgeBase()
    lm = EuresisLM.load(model_dir) if model_dir else EuresisLM.load()
    names = [f.name for f in kb.formulas]
    docs = [d for d in kb.documents() if d[0] == "formula"]
    retr = TextRetriever(docs)
    _, _, test = build(kb)
    rng = random.Random(seed)
    test = rng.sample(test, min(n_heldout, len(test)))
    sets = {"held-out phrasings": test, "natural questions": [(q, a) for q, a in NATURAL if a in names]}
    report = {}
    for label, qa in sets.items():
        ranks = {"word matching (previous)": [], "Euresis-LM": [], "fusion": [], "fusion (word-matching led)": []}
        for q, truth in qa:
            r_ret = [d[1] for d, _ in retr.search(q, len(names))]
            r_lm = [n for n, _ in lm.rank(q, names)]
            pos_r = {n: i for i, n in enumerate(r_ret)}
            pos_l = {n: i for i, n in enumerate(r_lm)}
            fused = sorted(names, key=lambda n: -(1 / (10 + pos_l.get(n, 999)) + 0.5 / (10 + pos_r.get(n, 999))))
            ranks["word matching (previous)"].append(_rr(r_ret, truth))
            ranks["Euresis-LM"].append(_rr(r_lm, truth))
            ranks["fusion"].append(_rr(fused, truth))
            fused2 = sorted(names, key=lambda n: -(0.5 / (10 + pos_l.get(n, 999)) + 1 / (10 + pos_r.get(n, 999))))
            ranks["fusion (word-matching led)"].append(_rr(fused2, truth))
        report[label] = {}
        log(f"{label} ({len(qa)} questions):")
        for k, v in ranks.items():
            v = np.array(v)
            res = {"top1": float(np.mean(v < 1)), "top5": float(np.mean(v < 5)), "top10": float(np.mean(v < 10))}
            report[label][k] = res
            log(f"  {k:28s} top-1 {res['top1'] * 100:5.1f}%   top-5 {res['top5'] * 100:5.1f}%   "
                f"top-10 {res['top10'] * 100:5.1f}%")
    return report


def bits_per_char(lm, texts):
    """Compression of unseen text: lower = the model has absorbed more of the language and knowledge."""
    import jax
    import jax.numpy as jnp
    tot_bits, tot_chars = 0.0, 0
    for t in texts:
        ids = lm.tok.encode(t).ids[: lm.cfg.ctx]
        if len(ids) < 2:
            continue
        x = jnp.array([ids])
        lp = np.asarray(jax.nn.log_softmax(lm._fwd(lm.params, x), -1))[0]
        nll = -sum(lp[i - 1, ids[i]] for i in range(1, len(ids)))
        tot_bits += nll / np.log(2)
        tot_chars += len(lm.tok.decode(ids[1:]))
    return tot_bits / max(1, tot_chars)


def unseen_abstracts(n=300, seed=0):
    import random
    from ..papers import read_abstracts
    papers = [t for _, t in read_abstracts()]
    rng = random.Random(seed)
    rng.shuffle(papers)                                     # same shuffle as build_with_papers(seed=0)
    unseen = papers[60000:]
    clean = [p.replace(" , ", ", ").replace(" . ", ". ").replace(" ( ", " (").replace(" ) ", ") ") for p in unseen]
    return random.Random(seed + 7).sample(clean, n)
