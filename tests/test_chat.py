"""Chat web app: pages, API and streaming (EURESIS_CHAT_FAKE avoids loading a language model)."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from euresis import chat


@pytest.fixture(scope="module")
def base(monkeypatch_module):
    monkeypatch_module.setenv("EURESIS_CHAT_FAKE", "1")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), chat.Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return [json.loads(c[6:]) for c in r.read().decode().split("\n\n") if c.startswith("data: ")]


def test_page_and_logo_are_served(base):
    code, ctype, body = get(base + "/")
    assert code == 200 and ctype.startswith("text/html") and b"/logo.png" in body and b"/api/chat" in body
    for name in ("/logo.png", "/logo-dark.png", "/mark.png", "/favicon.png"):
        code, ctype, body = get(base + name)
        assert code == 200 and ctype == "image/png" and body[:4] == b"\x89PNG"


def test_status_and_discoveries(base):
    st = json.loads(get(base + "/api/status")[2])
    assert {"backend", "daemon", "claims"} <= set(st) and st["fake"] is True
    for d in json.loads(get(base + "/api/discoveries")[2]):
        assert d["status"] in ("proved", "verified-numeric") and d["label"] and d["id"]


def test_ask_streams_tokens_and_claims(base):
    evs = post(base + "/api/chat", {"mode": "ask", "messages": [
        {"role": "user", "content": "damped oscillator quality factor"}]})
    kinds = [e["type"] for e in evs]
    assert "token" in kinds and kinds[-1] == "done"
    for e in evs:
        if e["type"] == "claim":       # cards carry the gate's status and honest label, never an upgraded one
            assert e["claim"]["status"] in ("proved", "verified-numeric", "refuted", "unverified", "candidate")
            assert e["claim"]["label"]


def test_research_mode_streams_steps(base):
    evs = post(base + "/api/chat", {"mode": "research", "messages": [{"role": "user", "content": "q"}]})
    kinds = [e["type"] for e in evs]
    assert "step" in kinds and "token" in kinds and kinds[-1] == "done"


def test_bad_requests(base):
    with pytest.raises(urllib.error.HTTPError) as e:
        post(base + "/api/chat", {"messages": []})
    assert e.value.code == 400
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base + "/api/claim/abc-000000000000")
    assert e.value.code == 404


def test_context_uses_exact_claim_ids():
    rows = chat.claims_index()
    if not rows:
        pytest.skip("empty registry")
    c = rows[len(rows) // 2]
    ctx, claims = chat.context_for(f"explain [{c['id']}]")
    assert claims[0]["id"] == c["id"] and c["id"] in ctx and f"status: {c['status']}" in ctx


def test_euresis_lm_chooses_laws_when_installed():
    from euresis.lm.model import EuresisLM
    steps = []
    lines = chat.kb_hits("How hot is a black hole?", emit=steps.append)
    assert lines and steps
    if EuresisLM.available():
        assert steps[0]["text"].startswith("Euresis-LM + word matching") and "Hawking" in steps[0]["text"]


def test_citation_check_flags_ids_not_supplied(monkeypatch):
    def fake_answer(turns, claims, emit):
        emit({"type": "token", "text": "As shown in [abc-0123456789ab], black holes are hot."})
    monkeypatch.setattr(chat, "_answer", fake_answer)
    evs = []
    chat.ask([{"role": "user", "content": "How hot is a black hole?"}], evs.append)
    text = "".join(e["text"] for e in evs if e["type"] == "token")
    assert "Citation check" in text and "abc-0123456789ab" in text.split("Citation check")[1]


def test_status_check_flags_statuses_without_gate_results(monkeypatch):
    def fake_answer(turns, claims, emit):
        emit({"type": "token", "text": "This result is verified-numeric in Euresis."})
    monkeypatch.setattr(chat, "_answer", fake_answer)
    monkeypatch.setattr(chat, "claim_hits", lambda q, k=8: [])
    evs = []
    chat.ask([{"role": "user", "content": "How hot is a black hole?"}], evs.append)
    assert "Status check" in "".join(e["text"] for e in evs if e["type"] == "token")
