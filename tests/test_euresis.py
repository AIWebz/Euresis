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


def test_data_discovery_recovers_kepler_and_reduced_mass():
    import warnings
    warnings.filterwarnings("ignore")
    from euresis.discover import DataDiscoverer, builtin
    dd = DataDiscoverer(KB, E, log=lambda *a: None)
    sets = {d.name: d for d in builtin()}
    k = dd.run(sets["orbits"])
    assert k["known"] == "Kepler's third law"
    b = dd.run(sets["balmer"])
    assert any("m_e/m_p" in line for line in b["lines"])


def test_idea_verifier_accepts_consistent_and_rejects_inconsistent():
    from euresis.connect import IdeaEngine
    ie = IdeaEngine(KB, E, None, None, log=lambda *a: None)
    good = {"title": "t", "equation": "v = sqrt(2*G*M/r)", "builds_on": ["Escape velocity"],
            "variables": [{"symbol": "v", "quantity_id": "escape_velocity", "new_quantity_dimension": ""},
                          {"symbol": "M", "quantity_id": "mass", "new_quantity_dimension": ""},
                          {"symbol": "r", "quantity_id": "radius", "new_quantity_dimension": ""}]}
    r = ie.verify(good)
    assert r["ok"] and r.get("known") == "Escape velocity"
    bad = dict(good, equation="v = G*M/r")
    assert not ie.verify(bad)["ok"]


def test_simulators_match_exact_physics():
    import math
    from euresis.simulate import orbit, pendulum, projectile
    assert abs(pendulum(1.0, theta0=1.0)["ratio_to_small_angle"] - 1.0663) < 1e-3   # elliptic-integral value
    assert abs(orbit()["period"] / 3.15581e7 - 1) < 1e-3                             # one sidereal year
    assert abs(projectile(v0=20.0)["range"] - 20.0 ** 2 / 9.80665) < 1e-3          # v²/g at 45°


def test_verifiers():
    from euresis.verify import cas, prove_z3, run_python
    assert prove_z3("x**2 + y**2 >= 2*x*y", {"x": "Real", "y": "Real"})["status"] == "proved"
    assert prove_z3("x**2 >= x", {"x": "Real"})["status"] == "refuted"
    assert cas("equal", "sin(x)**2 + cos(x)**2 == 1")["result"] is True
    assert run_python("print(6*7)")["stdout"].strip() == "42"


def test_literature_reports_unavailable_sources_honestly(tmp_path, monkeypatch):
    from euresis import literature
    def down(q, n):
        raise literature.SourceUnavailable("blocked")
    monkeypatch.setattr(literature, "SOURCES", {k: down for k in literature.SOURCES})
    monkeypatch.setattr(literature, "DB_PATH", tmp_path / "lit.db")
    lib = literature.Library(tmp_path / "lit.db")
    monkeypatch.setattr(literature, "Library", lambda path=None: lib)
    r = literature.novelty("black hole temperature inversely proportional to mass")
    assert r["verdict"].startswith("unchecked")
    lib.add([literature.Paper("test", "1", "Black hole temperature", "temperature of a black hole scales as 1/M",
                              2000, "", "")])
    assert lib.search("black hole temperature")[0].title == "Black hole temperature"


def test_pendulum_law_found_in_simulated_data():
    import warnings
    warnings.filterwarnings("ignore")
    from euresis.discover import DataDiscoverer, simulated
    dd = DataDiscoverer(KB, E, log=lambda *a: None)
    r = dd.run(next(d for d in simulated() if d.name == "pendulum_sim"))
    assert r["known"] == "Simple pendulum period"
