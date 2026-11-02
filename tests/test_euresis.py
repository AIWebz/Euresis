import math

import sympy as sp

from euresis.dimensions import D
from euresis.engine import Engine
from euresis.kb import KnowledgeBase, dim_of

KB = KnowledgeBase()
E = Engine(KB)


def test_every_formula_is_dimensionally_consistent():
    for f in KB.formulas:
        assert dim_of(f.eq.lhs, KB.dims) == dim_of(f.eq.rhs, KB.dims), f.name


def test_knowledge_base_size():
    s = KB.stats()
    assert s["formulas"] >= 180 and s["principles"] >= 50 and s["constants"] >= 30


def test_evaluate_escape_velocity_of_earth():
    f = KB.by_name("Escape velocity")
    v = E.evaluate(f, "escape_velocity", {"mass": 5.97217e24, "radius": 6.378137e6})
    assert abs(v - 11_180) < 20


def test_composition_derives_orbital_velocity():
    g = KB.by_name("Newton's law of universal gravitation")
    n2 = KB.by_name("Newton's second law")
    cen = KB.by_name("Centripetal acceleration")
    found = []
    for r in E.compose(g, n2):
        for r2 in E.compose(r, cen):
            k, ratio = E.find_known(r2)
            if k is not None:
                found.append((k.name, ratio))
    assert ("Circular orbital velocity", 1) in found


def test_dimensional_analysis_planck_length():
    syms = [sp.Symbol(s) for s in ("G", "hbar", "c")]
    exps, pis = E.rayleigh(D("L"), syms)
    assert exps == [sp.Rational(1, 2), sp.Rational(1, 2), sp.Rational(-3, 2)]
    vals = {s: KB.constants[s.name][1] for s in syms}
    assert math.isclose(float(E.monomial(syms, exps).subs(vals)), 1.616255e-35, rel_tol=1e-4)


def test_buckingham_pi_recovers_fine_structure_constant():
    syms = [sp.Symbol(s) for s in ("e", "epsilon_0", "hbar", "c")]
    _, pis = E.rayleigh(D("L"), syms)
    vals = {s: KB.constants[s.name][1] for s in syms}
    val = float(pis[0].subs(vals))
    alpha = KB.constants["alpha"][1]
    assert math.isclose(val, 4 * math.pi * alpha, rel_tol=1e-6) or math.isclose(1 / val, 4 * math.pi * alpha, rel_tol=1e-6)


def test_analogy_transfers_coulomb_to_gravity():
    pairs = {(a.name, b.name): m for a, b, m in E.analogies()}
    key = ("Newton's law of universal gravitation", "Coulomb's law")
    assert key in pairs
    rels = E.transfer_both(KB.by_name(key[0]), KB.by_name(key[1]), pairs[key])
    hits = {E.find_known(r)[0].name for r in rels if E.find_known(r)[0] is not None}
    assert "Gravitational potential energy" in hits


def test_equivalence_up_to_constant():
    a = KB.by_name("Escape velocity")
    b = KB.by_name("Circular orbital velocity")
    assert E.equivalent(b, a) in (sp.sqrt(2), 1 / sp.sqrt(2))
