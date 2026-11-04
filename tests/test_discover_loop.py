import pytest

from euresis import discover_loop as d
from euresis.registry import Registry


@pytest.fixture
def known():
    from euresis.theorems import LIBRARY
    return {k: str(v) for k, v in LIBRARY.items()}


def test_validation_rejects_non_candidates(known):
    assert d.validate("a/b", known)[1] == "not symmetric in a, b, c"
    assert d.validate("a+b+c", known)[1].startswith("not scale-invariant")
    assert d.validate("sqrt(a*b*c)/(a+b+c)", known)[1].startswith("must be a rational function")
    assert d.validate("(a*b+b*c+c*a)/(a**2+b**2+c**2)", known)[1] == "not minimised at a = b = c"
    assert d.validate("(a**4+b**4+c**4)/(a**2*b**2+b**2*c**2+c**2*a**2)", known)[1] == "ok"


def test_disguised_sums_and_products_are_rejected(known):
    s = "a/(2*(b + c)) + b/(2*(a + c)) + c/(2*(a + b)) + (a + b + c)*(1/c + 1/b + 1/a)/18"
    assert d.validate(s, known)[1].startswith("affine combination")
    p = "(a**2+b**2+c**2)*(a**3+b**3+c**3)/((a*b+b*c+c*a)*3*a*b*c)"
    assert d.validate(p, known)[1].startswith("product of known")
    assert d.validate("(a+b+c)**2/(a*b+b*c+c*a)", known)[1].startswith("affine combination")


def test_chain_implication(tmp_path):
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    for P, Q, k in (("x1", "x2", "2"), ("x2", "x3", "3")):
        cid = reg.add("inequality", f"{P}>{Q}", {"P": P, "Q": Q, "k": k}, source="t")
        reg.set_status(cid, "proved", "test", {})
    assert "chain" in d.implied_by_registry(reg, {"P": "x1", "Q": "x3", "k": "5"}, "new")
    assert d.implied_by_registry(reg, {"P": "x1", "Q": "x3", "k": "7"}, "new") == ""
    assert "already has constant" in d.implied_by_registry(reg, {"P": "x1", "Q": "x2", "k": "1"}, "new")


def test_round_without_model_records_only_gated_claims(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "STATE", tmp_path / "s.json")
    monkeypatch.setattr(d, "LOG", tmp_path / "l.md")
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    st = d.load_state()
    found = d.run_round(st, reg, use_llm=False, max_pairs=4, echo=lambda *a: None)
    for f in found:
        c = reg.get(f["claim"])
        assert c["status"] == "proved" and c["evidence"]["sharp"] and not c["novelty"].startswith("known")
