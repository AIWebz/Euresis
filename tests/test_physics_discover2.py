import numpy as np
import sympy as sp

from euresis import physics_discover2 as d
from euresis.registry import Registry


def test_seed_quantities_are_positive_and_finite():
    for fam, F in d.FAMILIES.items():
        X, Y = d.mesh(fam)
        for n, e in F["quantities"].items():
            v = d.evaluate(fam, e, X, Y)
            assert np.all(np.isfinite(v)) and v.min() > 0, (fam, n)


def test_validation_two_variables():
    k = d.FAMILIES["collision"]["quantities"]
    assert d.validate("collision", "m*e/(1 + m*e)", k)[1] == "ok"
    assert d.validate("collision", "(1 + e)*m/(1 + m) + 3", k)[1].startswith("affine")
    assert d.validate("collision", "m - 1", k)[1] == "not positive on the physical domain"


def test_disguised_one_variable_bounds_are_not_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "STATE", tmp_path / "s.json")
    monkeypatch.setattr(d, "LOG", tmp_path / "l.md")
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    st = d.load_state()
    for _ in range(3):                                   # two-body decay, collision, driven oscillator
        d.run_round(st, reg, use_llm=False, max_pairs=60, echo=lambda *a: None)
    claims = {c["statement"]: c for c in reg.claims()}
    gamma = [c for s, c in claims.items() if "Lorentz factor of product 1 ≥ 2 × speed of product 1" in s]
    assert gamma and gamma[0]["status"] == "proved" and "curve" in gamma[0]["novelty"]   # γ ≥ 2β in disguise
    assert st["discoveries"] == []


def test_isolated_minimum_detects_curves():
    a, b = d.syms("collision")
    assert d.isolated_minimum("collision", (a - sp.Rational(1, 2)) ** 2 + (b - sp.Rational(1, 2)) ** 2 + 1, sp.Integer(1), 0.5, 0.5)
    assert not d.isolated_minimum("collision", (a - b) ** 2 + 1, sp.Integer(1), 0.5, 0.5)
