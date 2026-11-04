from euresis import physics_discover as d
from euresis.registry import Registry


def test_validation():
    known = d.FAMILIES["relativity"]["quantities"]
    assert d.validate("relativity", "b**2*(1-b**2)", known)[1] == "ok"
    assert d.validate("relativity", "1/(1-b)", known)[1].startswith("a power or product of known")   # = γ × Doppler factor
    assert d.validate("relativity", "b - 1", known)[1] == "not positive on the physical domain"
    assert d.validate("relativity", "exp(b)", known)[1].startswith("only")
    assert d.validate("relativity", "x*b", known)[1].startswith("must depend on b")
    assert d.validate("relativity", "3/sqrt(1 - b**2) + b**2", known)[1].startswith("affine combination")


def test_finds_gamma_ge_2beta_and_rediscovers_esposito(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "STATE", tmp_path / "s.json")
    monkeypatch.setattr(d, "LOG", tmp_path / "l.md")
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    st = d.load_state()
    for _ in range(3):
        d.run_round(st, reg, use_llm=False, max_pairs=60, echo=lambda *a: None)
    stmts = [x["statement"] for x in st["discoveries"]]
    assert any("relativistic momentum / (mc) ≥ 4 × classical kinetic energy" in s for s in stmts)
    assert any("Esposito" in r["known"] for r in st["rediscoveries"])
    for x in st["discoveries"]:
        assert reg.get(x["claim"])["status"] == "proved"
