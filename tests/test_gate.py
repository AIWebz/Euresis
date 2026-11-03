"""Tests for the claims registry, verification gate, job queue, collection and write-ups."""
import json
import os
import time

import pytest

from euresis import collect, gate, jobs, scorecard, writeup
from euresis.registry import Registry, claim_id


@pytest.fixture
def reg(tmp_path):
    return Registry(tmp_path / "r.db", tmp_path / "claims.json")


def test_claim_ids_are_content_addressed(reg):
    p = {"claim": "x**2 >= 0", "variables": {"x": "Real"}}
    a = reg.add("z3", "x² ≥ 0", p, source="test")
    b = reg.add("z3", "x squared is non-negative", p, source="test")
    assert a == b == claim_id("z3", p)
    assert len(reg.claims()) == 1


def test_registry_rebuilds_from_committed_export(tmp_path, reg):
    cid = reg.add("z3", "x² ≥ 0", {"claim": "x**2 >= 0", "variables": {"x": "Real"}}, source="test")
    gate.check(reg, cid, log=lambda *a: None)
    fresh = Registry(tmp_path / "other.db", tmp_path / "claims.json")      # new machine, same export
    c = fresh.get(cid)
    assert c["status"] == "proved" and c["verifier"] == "z3"


def test_unknown_kind_rejected(reg):
    with pytest.raises(ValueError):
        reg.add("vibes", "it feels right", {}, source="test")


def test_gate_self_test_all_pass():
    r = scorecard.self_test(log=lambda *a: None)
    failed = [row for row in r["rows"] if not row["pass"]]
    assert not failed, failed


def test_gate_never_accepts_false_claims(reg):
    false = [
        ("z3", {"claim": "x + 1 > x + 2", "variables": {"x": "Real"}}),
        ("identity", {"lhs": "exp(x + y)", "rhs": "exp(x) + exp(y)", "symbols": ["x", "y"]}),
        ("inequality", {"P": "a/(b+c)+b/(c+a)+c/(a+b)", "Q": "(a**2+b**2+c**2)/(a*b+b*c+c*a)", "k": "1"}),
        ("constant", {"a": "2", "b": "1", "value": "sqrt(2)", "digits": 50, "depth": 300}),
    ]
    for kind, p in false:
        cid = reg.add(kind, f"false {kind}", p, source="test")
        assert gate.check(reg, cid, log=lambda *a: None) == "refuted", (kind, reg.get(cid)["evidence"])


def test_crashing_verifier_is_unverified_not_proved(reg):
    cid = reg.add("identity", "unparseable", {"lhs": "((", "rhs": "1", "symbols": []}, source="test")
    assert gate.check(reg, cid, log=lambda *a: None) == "unverified"


def test_slow_claims_go_to_the_job_queue_and_worker_runs_them(reg, monkeypatch):
    calls = []
    monkeypatch.setitem(gate.VERIFIERS, "orbit", ("fake-prover", lambda p: (calls.append(p) or "proved", {"ok": 1})))
    cid = reg.add("orbit", "orbit", {"p1": 0.1, "p2": 0.2, "tau": 1.0}, source="test")
    gate.run(reg, log=lambda *a: None)
    assert reg.get(cid)["status"] == "candidate"            # not run inline
    assert [j["state"] for j in reg.jobs()] == ["queued"]
    gate.run(reg, log=lambda *a: None)                       # no duplicate job
    assert len(reg.jobs()) == 1
    assert jobs.work(reg, log=lambda *a: None) == 1
    assert reg.get(cid)["status"] == "proved" and len(calls) == 1
    assert reg.jobs()[0]["state"] == "done"


def test_stale_running_jobs_are_requeued(reg):
    jid = reg.submit("gate", {"claim": "nothing"})
    reg.claim_job()
    assert reg.requeue_stale(older_than_s=-1) == 1
    assert reg.jobs()[0]["state"] == "queued" and reg.jobs()[0]["id"] == jid


def test_failed_job_records_error(reg):
    reg.submit("no-such-kind", {})
    jobs.work(reg, log=lambda *a: None)
    j = reg.jobs()[0]
    assert j["state"] == "failed" and "no handler" in j["error"]


def test_orbit_log_parsing_and_ingestion(reg):
    log = """newton 5: ...
F(c) enclosure: [3]([-1e-13,1e-13],[-1e-13,1e-13],[-1e-13,1e-13])
radius 1.0000000000000001e-09: ||Id - R F'(I)||_inf <= 0.00011379385507304107  -> K(I) inside I
PROVED: unique zero in box
  x0 in [0.33940741198584667,0.33940741199585612]  width 1e-11
  x1 in [0.5361849781491369,0.53618497815372035]  width 4e-12
  x2 in [3.1454093825280375,3.1454093825479568]  width 2e-11
  period 2*tau in [6.2908187650560751,6.2908187650959136]
"""
    ev = gate.parse_orbit_output(log)
    assert ev["period"] == [6.2908187650560751, 6.2908187650959136]
    assert ev["box"]["tau"][0] < 3.14540938253 < ev["box"]["tau"][1]
    assert ev["contraction_bounds"] == [0.00011379385507304107]
    cid = reg.add("orbit", "I.A1", {"p1": 0.3394074123, "p2": 0.536184978, "tau": 3.145409}, source="test")
    reg.submit("gate", {"claim": cid})
    assert gate.ingest_orbit_log(reg, cid, log) == "proved"
    assert reg.jobs()[0]["state"] == "done"                  # queued job closed
    assert gate.ingest_orbit_log(reg, cid, log.replace("PROVED: unique zero in box", "NOT PROVED")) == "unverified"


def test_pretty_formulas_parse_to_sympy():
    assert collect._pretty_to_sympy("3n² + 3n + 1") == "3*n**2 + 3*n + 1"
    assert collect._pretty_to_sympy("-2·n^3·(n + 1)") == "-2*n**3*(n + 1)"
    assert collect._pretty_to_sympy("(-2) / (1 − 2·G (Catalan))") == "(-2) / (1 - 2*catalan)"
    assert collect._pretty_to_sympy("(-8 − 4·√3) / (-4 + √3)") == "(-8 - 4*sqrt(3)) / (-4 + sqrt(3))"


def test_labels_are_honest(reg):
    cid = reg.add("constant", "1+√2", {"a": "2", "b": "1", "value": "1 + sqrt(2)", "digits": 50, "depth": 300},
                  source="test", novelty="known (classical)")
    gate.check(reg, cid, log=lambda *a: None)
    c = reg.get(cid)
    assert gate.label(c) == "numerically verified, not proved"
    assert not gate.is_discovery(c)


def test_writeups_only_for_verified_unknown_claims(reg, tmp_path, monkeypatch):
    monkeypatch.setattr(writeup, "OUT", tmp_path / "w")
    good = reg.add("z3", "x² + 1 > 0", {"claim": "x**2 + 1 > 0", "variables": {"x": "Real"}}, source="test")
    known = reg.add("z3", "x² ≥ 0", {"claim": "x**2 >= 0", "variables": {"x": "Real"}}, source="test",
                    novelty="known (trivial)")
    bad = reg.add("z3", "x² ≥ x", {"claim": "x**2 >= x", "variables": {"x": "Real"}}, source="test")
    for cid in (good, known, bad):
        gate.check(reg, cid, log=lambda *a: None)
    paths = writeup.run(reg, log=lambda *a: None)
    assert [p.stem for p in paths] == [good]
    text = paths[0].read_text()
    assert "proved" in text and "Reproduce" in text and (tmp_path / "w" / f"{good}.tex").exists()


@pytest.mark.skipif(not os.environ.get("EURESIS_SLOW"), reason="rigorous orbit proof takes ~20 min (EURESIS_SLOW=1)")
def test_orbit_prover_proves_known_orbit(reg):
    cid = reg.add("orbit", "I.A1 (catalogued)", {"p1": 0.3394074123, "p2": 0.536184978, "tau": 3.145409},
                  source="test")
    assert gate.check(reg, cid, log=lambda *a: None) == "proved"
    lo, hi = reg.get(cid)["evidence"]["period"]
    assert lo < 6.29081876505 < hi
