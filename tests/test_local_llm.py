import pytest

from euresis import local_llm


def test_prompt_uses_qwen3_chat_and_tool_format():
    tools = [{"name": "prove", "description": "Z3", "input_schema": {"type": "object", "properties": {}}}]
    p = local_llm.render("SYS", [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"},
                                 {"role": "tool", "content": "r1"}, {"role": "tool", "content": "r2"}], tools, think=False)
    assert p.startswith("<|im_start|>system\nSYS\n\n# Tools")
    assert '"name": "prove"' in p and "<tool_call>" in p
    assert "<|im_start|>user\n<tool_response>\nr1\n</tool_response>\n<tool_response>\nr2\n</tool_response><|im_end|>" in p
    assert p.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")          # non-thinking switch
    assert local_llm.render("S", [{"role": "user", "content": "q"}], None, think=True).endswith("assistant\n")


def test_tool_calls_are_parsed_and_thinking_hidden():
    text = ('<think>let me check</think>I will prove it.\n<tool_call>\n{"name": "prove", "arguments": '
            '{"claim": "x**2 >= 0", "variables": {"x": "Real"}}}\n</tool_call>\n<tool_call>{bad json}</tool_call>')
    visible, calls = local_llm.parse(text)
    assert visible == "I will prove it."
    assert calls[0] == {"name": "prove", "arguments": {"claim": "x**2 >= 0", "variables": {"x": "Real"}}}
    assert calls[1]["name"] == "_invalid"


def test_local_loop_routes_claims_through_gate(tmp_path, monkeypatch):
    """Scripted stand-in for the 14B model: checks the loop → tools → gate → report wiring."""
    from euresis import literature
    from euresis.agent import ReasoningCore
    from euresis.engine import Engine
    from euresis.kb import KnowledgeBase
    from euresis.registry import Registry, claim_id

    true_p = {"claim": "x**2 + y**2 >= 2*x*y", "variables": {"x": "Real", "y": "Real"}}
    false_p = {"lhs": "(x+y)**2", "rhs": "x**2+y**2", "symbols": ["x", "y"]}
    turns = [
        {"text": "", "raw": "", "calls": [
            {"name": "submit_claim", "arguments": {"kind": "z3", "statement": "x²+y² ≥ 2xy", "payload": true_p,
                                                   "known_as": "AM-GM"}},
            {"name": "submit_claim", "arguments": {"kind": "identity", "statement": "(x+y)² = x²+y²",
                                                   "payload": false_p}},
            {"name": "prove", "arguments": {}}]},
        {"text": f"AM-GM [{claim_id('z3', true_p)}]; wrong square [{claim_id('identity', false_p)}].",
         "raw": "done", "calls": []},
    ]
    seen = []

    def fake_complete(system, messages, tools, think=False, **kw):
        seen.append(messages[-1])
        return {**turns.pop(0), "seconds": 0.0, "prompt_tokens": 1, "completion_tokens": 1}

    class FakeLLM:
        def tokenize(self, b):
            return b.split()

        def n_ctx(self):
            return 10 ** 6

    monkeypatch.setattr(local_llm, "available", lambda: True)
    monkeypatch.setattr(local_llm, "load", lambda **kw: FakeLLM())
    monkeypatch.setattr(local_llm, "complete", fake_complete)
    monkeypatch.setattr(literature, "novelty", lambda s, k=None, **kw: {"verdict": "no close match", "closest": []})
    kb = KnowledgeBase()
    core = ReasoningCore(kb, Engine(kb), None, None, registry=Registry(tmp_path / "r.db", tmp_path / "c.json"),
                         log=lambda *a: None)
    report = core.research("test question", backend="local")
    reg = core.registry
    assert reg.get(claim_id("z3", true_p))["status"] == "proved"
    assert reg.get(claim_id("identity", false_p))["status"] == "refuted"
    assert "local Qwen3-14B" in reg.get(claim_id("z3", true_p))["source"]
    assert "unknown or unavailable tool prove" in seen[-1]["content"]     # ungated prover is not offered
    assert "refuted" in report and "proved" in report


@pytest.mark.skipif(not local_llm.available(), reason="local 14B model not installed")
def test_local_model_answers_and_calls_tools():
    r = local_llm.complete("You are a precise assistant.", [{"role": "user", "content": "What is 17*23? Reply with the number only."}],
                           max_tokens=20, temperature=0.0)
    assert "391" in r["text"]
