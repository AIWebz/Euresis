"""Training corpus for Euresis-LM, generated from Euresis' own knowledge.

Three kinds of text:
* **knowledge prose** — every law, principle, constant, quantity and field,
  written out in several phrasings;
* **question → law pairs** — natural questions about the quantities in each law
  (with everyday synonyms), answered with the law's name: this teaches the model
  to *understand* what a question is about;
* **explanations** — "explain <law>" → a description of what it relates.

Question phrasings are split: TRAIN templates are used for training, TEST
templates are held out entirely so evaluation measures generalisation to new
wording, not memorisation.
"""
from __future__ import annotations

import random

from ..kb import KnowledgeBase

FIELD_WORDS = {
    "mechanics": ["motion", "moving objects", "forces and motion"], "gravitation": ["gravity", "orbits", "planets and moons"],
    "waves": ["waves", "sound and vibration"], "optics": ["light", "lenses and light"],
    "thermodynamics": ["heat", "engines and heat", "temperature and energy"],
    "statistical_mechanics": ["gases", "molecules in a gas", "thermal motion"],
    "electromagnetism": ["electricity and magnetism", "electric and magnetic fields", "charges"],
    "circuits": ["electric circuits", "electronics"], "fluids": ["fluids", "liquids and gases in motion", "flow"],
    "materials": ["materials", "solids under load"], "relativity": ["relativity", "objects near light speed"],
    "quantum": ["quantum mechanics", "atoms and photons"], "atomic": ["atoms", "the hydrogen atom"],
    "nuclear": ["nuclei", "radioactivity"], "astrophysics": ["stars", "the universe", "black holes and stars"],
    "astronomy": ["astronomy", "the sky"], "chemistry": ["chemical reactions", "molecules and reactions", "solutions"],
    "biology": ["living things", "populations and organisms", "cells and organisms"],
    "earth_science": ["the Earth", "the atmosphere and climate", "earthquakes and the planet"],
    "information": ["information", "communication and computation"], "geometry": ["shapes", "geometry"],
    "mathematics": ["mathematics"], "physics": ["physics"], "method": ["science"],
}

SYNONYMS = {
    "velocity": ["speed", "how fast it moves"], "radius": ["size", "radius"], "distance": ["separation", "distance"],
    "mass": ["mass", "weight", "how heavy it is"], "temperature": ["temperature", "how hot it is"],
    "luminosity": ["brightness", "luminosity", "power output"], "period": ["period", "cycle time"],
    "energy": ["energy"], "force": ["force", "push or pull"], "pressure": ["pressure"], "time": ["time", "duration"],
    "frequency": ["frequency", "pitch"], "wavelength": ["wavelength", "colour"], "density": ["density"],
    "radiant flux density": ["flux", "irradiation", "incident radiation"], "metabolic rate": ["metabolism"],
    "lifespan": ["lifespan", "life expectancy"], "population size": ["population", "number of individuals"],
    "electric charge": ["charge"], "electric current": ["current"], "magnetic flux density": ["magnetic field"],
    "viscosity": ["viscosity", "thickness of a fluid"], "dynamic viscosity": ["viscosity"],
}

TRAIN_TEMPLATES = [
    "How does {a} depend on {b}?", "What law relates {a} and {b}?", "What determines {a} in {f}?",
    "Which equation connects {a}, {b} and {c}?", "Why does {a} change when {b} changes?",
    "What is the formula for {a} in {f}?", "In {f}, how is {a} related to {b}?", "What sets the {a} in {f}?",
    "How can I calculate {a} from {b} and {c}?", "What happens to {a} if {b} doubles?",
]
TEST_TEMPLATES = [
    "Explain the relationship between {a} and {b}.", "If {b} increases, what happens to {a}?",
    "Is there a connection between {a} and {b} in {f}?", "Find the law governing {a} given {b}.",
]


def _name(kb, q, rng):
    nm = kb.qname(q).split(" (")[0]
    alts = SYNONYMS.get(q, []) + SYNONYMS.get(nm, [])
    return rng.choice(alts + [nm, nm]) if alts else nm


def law_questions(kb: KnowledgeBase, templates, n_per_law=6, seed=0):
    rng = random.Random(seed)
    out = []
    for f in kb.formulas:
        qs = sorted(f.quantities)
        if not qs:
            continue
        lhs = f.sym_to_q.get(f.eq.lhs) if f.eq.lhs in f.sym_to_q else qs[0]
        for _ in range(n_per_law):
            others = [q for q in qs if q != lhs] or qs
            b, c = rng.choice(others), rng.choice(others + [lhs])
            t = rng.choice(templates)
            q = t.format(a=_name(kb, lhs, rng), b=_name(kb, b, rng), c=_name(kb, c, rng),
                         f=rng.choice(FIELD_WORDS.get(f.domain, [f.domain])))
            out.append((q, f.name))
    return out


def explain(kb, f, rng):
    qn = ", ".join(kb.qname(q) for q in sorted(f.quantities))
    cn = ", ".join(kb.constants[c.name][0] for c in f.constants)
    fw = rng.choice(FIELD_WORDS.get(f.domain, [f.domain]))
    s = f"The {f.name} is a law of {f.domain.replace('_', ' ')}: {f.pretty()}. It relates {qn}"
    s += f", using the {cn}." if cn else "."
    s += f" It describes {fw}."
    return s


def build(kb: KnowledgeBase | None = None, seed=0):
    kb = kb or KnowledgeBase()
    rng = random.Random(seed)
    docs = []
    for f in kb.formulas:
        for _ in range(3):
            docs.append(explain(kb, f, rng))
        docs.append(f"explain: {f.name}\nanswer: {explain(kb, f, rng)}")
    for p in kb.principles:
        for _ in range(4):
            docs.append(f"{p.name} ({p.domain.replace('_', ' ')}). {p.statement}")
        docs.append(f"explain: {p.name}\nanswer: {p.statement}")
    for k, (name, v, unit, dim, exact) in kb.constants.items():
        docs.append(f"The {name} ({k}) has the value {v:.6g} {unit}{' exactly' if exact else ''}.")
    for q, (name, dim) in kb.quantities.items():
        laws = [f.name for f in kb.formulas if q in f.quantities][:6]
        if laws:
            docs.append(f"The quantity {name} has SI dimension {dim}. It appears in: {', '.join(laws)}.")
    train_qa = law_questions(kb, TRAIN_TEMPLATES, n_per_law=24, seed=seed)
    test_qa = law_questions(kb, TEST_TEMPLATES, n_per_law=2, seed=seed + 1)
    for q, law in train_qa:
        docs.append(f"question: {q}\nlaw: {law}")
    rng.shuffle(docs)
    return docs, train_qa, test_qa
