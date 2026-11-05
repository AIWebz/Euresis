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
    path.write_text("dose,response,dose_in_other_units,noise\n" + "\n".join(f"{a},{b},{c},{d}" for a, b, c, d in zip(x, y, dup, noise)))
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    found = F.analyse(path, {"source": "test", "doi": "10.0/test", "title": "planted", "file": "planted.csv"}, reg,
                      echo=lambda *a: None)
    stmts = [f["statement"] for f in found]
    assert any("'response' follows a power law in 'dose'" in s for s in stmts)
    assert not any("'dose_in_other_units'" in s and "'dose'" in s for s in stmts)   # unit conversion skipped
    assert not any("'noise'" in s for s in stmts)
    c = reg.get(found[0]["claim"])
    assert c["status"] == "verified-numeric" and gate.label(c).startswith("confirmed on held-out data")


def test_timestamp_columns_are_not_laws(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "CACHE", tmp_path)
    monkeypatch.setattr(F, "LOG", tmp_path / "log.md")
    F._SEEN_PAIRS.clear()
    rng = np.random.default_rng(1)
    start = np.cumsum(rng.uniform(1, 5, 300))
    end = start + rng.uniform(0.5, 2, 300)
    path = tmp_path / "times.csv"
    path.write_text("tstart,tend\n" + "\n".join(f"{a},{b}" for a, b in zip(start, end)))
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    assert F.analyse(path, {"source": "t", "doi": "", "title": "t", "file": "times.csv"}, reg, echo=lambda *a: None) == []


def test_headerless_csv_gets_column_numbers(tmp_path):
    rng = np.random.default_rng(2)
    x = rng.uniform(1, 10, 200)
    path = tmp_path / "noheader.csv"
    path.write_text("\n".join(f"{a},{2 * a ** 2}" for a in x))
    T = F.load_table(path)
    assert list(T.columns) == ["column 1 (unlabelled)", "column 2 (unlabelled)"] and len(T) == 200


def test_geometry_and_same_quantity_filters():
    assert F.geometric("Area [µm^2]", "Volume [µm^3]", 0.667)
    assert F.geometric("EqRadius [µm]", "Area [µm^2]", 0.5)
    assert not F.geometric("fish_length_mm", "otolith_mass_g", 0.81)
    assert not F.geometric("temperature", "pressure", 1.0)


def test_generic_column_names_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "CACHE", tmp_path)
    monkeypatch.setattr(F, "LOG", tmp_path / "log.md")
    F._SEEN_PAIRS.clear()
    rng = np.random.default_rng(3)
    x = rng.uniform(1, 10, 300)
    path = tmp_path / "g.csv"
    path.write_text("Column1.6,Column1.9\n" + "\n".join(f"{a},{3 * a + rng.normal(0, 0.5)}" for a in x))
    reg = Registry(tmp_path / "r.db", tmp_path / "c.json")
    assert F.analyse(path, {"source": "t", "doi": "", "title": "t", "file": "g.csv"}, reg, echo=lambda *a: None) == []


def test_known_families():
    assert F.known_family("TankpH", "TankCO2")
    assert not F.known_family("fish_length_mm", "otolith_width_um")


def test_same_quantity_detection():
    assert F.same_quantity("pKa_pred", "pKa_exp") and F.same_quantity("calculated_pKa", "pKa_expt")
    assert F.same_quantity("x_gse_mms1", "x_gse_mms2")
    assert not F.same_quantity("fish_length_mm", "otolith_width_um")
    assert not F.same_quantity("diameter", "mass")
