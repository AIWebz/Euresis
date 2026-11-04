"""The reasoning core may propose anything, but only the verification gate sets a claim's status.

These tests drive the tool loop with a scripted stand-in for the Claude client, so they check the
wiring (registry → gate → novelty → report), not the model.
"""
from types import SimpleNamespace as NS

import pytest

from euresis import gate, literature
from euresis.agent import ReasoningCore
from euresis.engine import Engine
from euresis.kb import KnowledgeBase
from euresis.registry import Registry, claim_id

TRUE_KNOWN = {"claim": "x**2 + y**2 >= 2*x*y", "variables": {"x": "Real", "y": "Real"}}
TRUE_NEW = {"claim": "x**4 + y**4 + 2 >= 4*x*y", "variables": {"x": "Real", "y": "Real"}}
FALSE = {"claim": "x**2 >= x", "variables": {"x": "Real"}}
FALSE_ID = {"lhs": "sin(x)**2", "rhs": "1 - cos(x)", "symbols": ["x"]}


def tool(i, name, **inp):
    return NS(type="tool_use", id=f"t{i}", name=name, input=inp)


class FakeClient:
    """Plays back a fixed sequence of assistant turns."""
    def __init__(self, turns):
        self.turns, self.calls = list(turns), []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        content = self.turns.pop(0)
        stop = "tool_use" if any(b.type == "tool_use" for b in content) else "end_turn"
        return NS(content=content, stop_reason=stop)


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.setattr(literature, "novelty", lambda s, k=None, **kw: {
        "verdict": "no close match in 3 papers searched — not proof of novelty (searched: test)",
        "best_similarity": 0.1, "closest": []})
    kb = KnowledgeBase()
    return ReasoningCore(kb, Engine(kb), None, None, registry=Registry(tmp_path / "r.db", tmp_path / "c.json"),
                         log=lambda *a: None)


def test_every_claim_goes_through_gate(core):
    ids = {k: claim_id(kind, p) for k, kind, p in [("known", "z3", TRUE_KNOWN), ("new", "z3", TRUE_NEW),
                                                    ("false", "z3", FALSE), ("fid", "identity", FALSE_ID)]}
    client = FakeClient([
        [tool(1, "propose", hypotheses=[{"statement": "AM-GM style bounds hold", "test": "Z3"}],
              plan=["state", "prove"])],
        [tool(2, "submit_claim", kind="z3", statement="x²+y² ≥ 2xy", payload=TRUE_KNOWN, known_as="AM-GM"),
         tool(3, "submit_claim", kind="z3", statement="x⁴+y⁴+2 ≥ 4xy", payload=TRUE_NEW),
         tool(4, "submit_claim", kind="z3", statement="x² ≥ x", payload=FALSE),
         tool(5, "submit_claim", kind="identity", statement="sin²x = 1 − cos x", payload=FALSE_ID),
         tool(6, "submit_claim", kind="z3", statement="malformed", payload={})],
        [NS(type="text", text=f"Known [{ids['known']}], new [{ids['new']}], false [{ids['false']}], "
                              f"bogus [z3-000000000000]. I am sure this is a discovery.")],
    ])
    report = core.research("test question", max_turns=5, client=client)

    reg = core.registry
    assert reg.get(ids["known"])["status"] == "proved"
    assert reg.get(ids["known"])["novelty"].startswith("known")
    assert reg.get(ids["new"])["status"] == "proved"
    assert reg.get(ids["false"])["status"] == "refuted"
    assert reg.get(ids["fid"])["status"] == "refuted"
    assert len(reg.claims()) == 4                       # the malformed payload was never registered

    disc = [c for c in reg.claims() if gate.is_discovery(c)]
    assert [c["id"] for c in disc] == [ids["new"]]      # proved AND not known — nothing else

    assert f"{ids['false']} ⟨false⟩" in report
    assert f"{ids['known']} ⟨proved; already known⟩" in report
    assert "z3-000000000000 ⟨NOT IN REGISTRY — unverified⟩" in report
    assert "**Discoveries (proved AND not known):** 1" in report
    assert ids["fid"] in report.split("Submitted but not cited")[1]

    msgs = client.calls[2]["messages"]                          # same list, later extended with the reply
    results = [m for m in msgs if m["role"] == "user"][-1]["content"]   # tool results the model saw
    assert all(r["type"] == "tool_result" for r in results)
    assert "missing" in results[-1]["content"]


def test_no_ungated_prover_tool():
    from euresis.agent import TOOLS
    names = {t["name"] for t in TOOLS}
    assert "submit_claim" in names and "propose" in names
    assert not names & {"prove", "check_lean"}          # formal claims can only enter through the gate


def test_existing_verdict_is_reused_not_overwritten(core):
    r1 = core.submit_claim("z3", "x² ≥ x", FALSE)
    r2 = core.submit_claim("z3", "x squared is at least x", FALSE, known_as="")
    assert r1["status"] == r2["status"] == "refuted" and "reused" in r2["note"]


def test_partial_report_when_run_stops_early(core):
    client = FakeClient([[tool(1, "submit_claim", kind="z3", statement="x² ≥ x", payload=FALSE)]] * 2)
    report = core.research("q", max_turns=2, client=client)
    assert report and "ended before Claude wrote its report" in report and "**refuted**" in report
