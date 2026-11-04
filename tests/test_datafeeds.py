import numpy as np

from euresis import datafeeds as F, gate
from euresis.registry import Registry


def test_planted_law_found_and_duplicates_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "CACHE", tmp_path)
    monkeypatch.setattr(F, "LOG", tmp_path / "log.md")
    F._SEEN_PAIRS.clear()
    rng = np.random.default_rng(0)
    x = rng.uniform(1, 100, 400)
    y = 3.0 * x ** 1.5 * np.exp(rng.normal(0, 0.03, 400))        # a power law with 3 % noise
    dup = 2.54 * x                                                 # the same quantity in other units
    noise = rng.normal(0, 1, 400)
    path = tmp_path / "planted.csv"
    path.write_text("x,y,x_in_other_units,noise\n" + "\n".join(f"{a},{b},{c},{d}" for a, b, c, d in zip(x, y, dup, noise)))
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    found = F.analyse(path, {"source": "test", "doi": "10.0/test", "title": "planted", "file": "planted.csv"}, reg,
                      echo=lambda *a: None)
    stmts = [f["statement"] for f in found]
    assert any("'y' follows a power law in 'x'" in s for s in stmts)
    assert not any("x_in_other_units' " in s and "'x'" in s for s in stmts)       # unit conversion skipped
    assert not any("'noise'" in s for s in stmts)
    c = reg.get(found[0]["claim"])
    assert c["status"] == "verified-numeric" and gate.label(c).startswith("confirmed on held-out data")
