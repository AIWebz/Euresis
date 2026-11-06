"""Euresis Chat: a chat web app (in the style of Claude or ChatGPT) over Euresis' reasoning core.

    python -m euresis chat            # then open http://127.0.0.1:8765

Two modes, both streamed to the page as they run:

* **Ask** — a conversational answer grounded in Euresis' knowledge base and its gate-verified results. Euresis-LM
  (Euresis' own 5.8 M-parameter model) and word matching choose the relevant laws; the reply is written by Claude
  if ANTHROPIC_API_KEY is set, else the local Qwen3 model, else it is an offline summary of what is known.
* **Research** — the full reasoning loop: the model proposes claims, the verification gate decides their
  status, and the page shows every step and every claim with its honest label (proved / numerically verified /
  confirmed on held-out data / refuted).

Only the gate sets a claim's status; the chat never upgrades one. The server uses only the standard library.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .registry import ROOT, Registry

WEB = Path(__file__).parent / "web"
SPACE = ROOT / "space"
MODEL_LOCK = threading.Lock()          # one generation at a time (a local model can't serve two at once)
IDLE_UNLOAD_MIN = 10                   # free the local model after this many idle minutes (discovery can use it)
_LAST_USE = [0.0]
_CACHE: dict = {}

ASK_SYSTEM = (
    "You are Euresis, a scientific discovery engine, talking with a user in a chat. Answer clearly and directly, "
    "using the <knowledge> block: it holds textbook laws from Euresis' knowledge base and results from Euresis' "
    "own verification gate, each with its exact status. Rules: (1) Never call something proved, verified or new "
    "unless the knowledge block gives it that status; cite a claim id only if it appears in the knowledge block, copied "
    "exactly, and only for the result it belongs to; textbook laws have no claim id. "
    "(2) 'novelty unchecked' means nobody has checked whether it is already published — say so rather than calling "
    "it new. (3) Empirical findings are evidence from data, not proofs. (4) If the knowledge block does not cover "
    "the question, answer from general knowledge and say that this part is not verified by Euresis; suggest "
    "Research mode when a claim could be proved. (5) Textbook laws are established science, not Euresis results: give them no gate status. Use Markdown; "
    "write equations in plain text with Unicode symbols (e.g. T = ħc³ / (8πGMk_B)), not LaTeX.")

STOP = set("the of and a an to in is for by on with as at from that this be are or it its into what which how why "
           "does do can could would should about any there their them they you your me my we our has have had was "
           "were will shall than then also more most less such tell explain show give find new euresis".split())
CATEGORY = {"games_log.md": "Games", "physics2_log.md": "Physics & economics", "physics_discovery_log.md": "Physics",
            "datafeeds_log.md": "Paper data", "music_n_log.md": "Music", "music_log.md": "Music",
            "linguistics_log.md": "Language", "discovery_log.md": "Mathematics"}
LOG_LINE = re.compile(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d) (DISCOVERY|FINDING|SOLVED|THEOREM)\b\s*(?:\(([^)]*)\))?:?\s*"
                      r"(.*?)\s*\[([a-z]{3}-[0-9a-f]{12})\]\s*$")
CLAIM_ID = re.compile(r"\b([a-z]{3}-[0-9a-f]{12})\b")
STATUS_WORDS = re.compile(r"verified-numeric|numerically verified|\b(?:is|was|been|are|were) (?:proved|proven|refuted)\b|"
                          r"\bconfirmed on held-out", re.I)


# ------------------------------------------------------------------ knowledge
def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", text.lower()) if w not in STOP}


def claims_index(max_age: float = 300.0) -> list[dict]:
    """All registry claims with their search words, refreshed every couple of minutes."""
    c = _CACHE.get("claims")
    if c and time.time() - c[0] < max_age:
        return c[1]
    rows = Registry().claims()
    for r in rows:
        r["_w"] = _words(r["statement"] + " " + r.get("kind", "") + " " + str(r.get("novelty", "")))
    _CACHE["claims"] = (time.time(), rows)
    return rows


def label(c: dict) -> str:
    from . import gate
    try:
        return gate.label(c)
    except KeyError:
        return c.get("status", "unknown")


def overview() -> str:
    """A few always-included facts, so questions like 'what have you solved?' have an answer."""
    rows = claims_index()
    by = {}
    for r in rows:
        by.setdefault(r["kind"], {}).setdefault(r["status"], 0)
        by[r["kind"]][r["status"]] += 1
    lines = ["Euresis' registry (claims by kind and gate status): " +
             "; ".join(f"{k}: " + ", ".join(f"{n} {s}" for s, n in v.items()) for k, v in sorted(by.items()))]
    games = [r for r in rows if r["kind"] == "game" and r["status"] == "proved"]
    if games:
        top = sorted(games, key=lambda r: int(r["payload"].get("period", 0)), reverse=True)[:3]
        lines.append("Octal games with the longest proved periods: " + "; ".join(
            f"0.{r['payload']['code']} (pre-period {r['payload']['preperiod']}, period {r['payload']['period']}) "
            f"[{r['id']}]" for r in top))
    return "\n".join(lines)


def _kb():
    if "retr" not in _CACHE:
        from .kb import KnowledgeBase
        from .model import TextRetriever
        kb = KnowledgeBase()
        _CACHE["kb"], _CACHE["retr"] = kb, TextRetriever(kb.documents())
    return _CACHE["kb"], _CACHE["retr"]


def euresis_lm():
    """Euresis' own language model (5.8 M parameters, trained on its knowledge base), or None."""
    if "lm" not in _CACHE:
        try:
            from .lm.model import EuresisLM
            _CACHE["lm"] = EuresisLM.load() if EuresisLM.available() else None
        except Exception:
            _CACHE["lm"] = None
    return _CACHE["lm"]


def relevant_laws(q: str, k: int = 5) -> tuple[list, bool]:
    """The laws a question is about: Euresis-LM ranks every law in the knowledge base and is fused with word
    matching (word-matching led), the combination that measured best in `euresis lm eval` (74% top-1 on held-out
    phrasings vs 68% for word matching alone)."""
    kb, retr = _kb()
    hits = retr.search(q, 14)
    laws = [kb.by_name(d[1]) for d, _ in hits if d[0] == "formula" and kb.by_name(d[1])]
    lm = euresis_lm()
    if lm is None or not kb.formulas:
        return laws[:k], False
    names = [f.name for f in kb.formulas]
    r_lm = {n: i for i, (n, _) in enumerate(lm.rank(q, names))}
    r_wm = {f.name: i for i, f in enumerate(laws)}
    fused = sorted(names, key=lambda n: -(0.5 / (10 + r_lm.get(n, 999)) + 1 / (10 + r_wm.get(n, 999))))
    return [kb.by_name(n) for n in fused[:k]], True


def kb_hits(q: str, k: int = 5, emit=None) -> list[str]:
    try:
        kb, retr = _kb()
        laws, used_lm = relevant_laws(q, k)
        if emit:
            emit({"type": "step", "text": ("Euresis-LM + word matching" if used_lm else "word matching") +
                  " chose the relevant laws: " + "; ".join(f.name for f in laws)})
        out = [f"- [textbook law] {f.name}: {f.pretty()}" for f in laws]
        for (kind, title, text), _ in retr.search(q, 8):          # principles and constants by word matching
            if kind != "formula" and len(out) < k + 3:
                out.append(f"- [textbook {kind}] {title}: {text[:300]}")
        return out
    except Exception:          # the chat still works without the knowledge base
        return []


def claim_hits(q: str, k: int = 8) -> list[dict]:
    rows = claims_index()
    ids = set(CLAIM_ID.findall(q))
    codes = set(re.findall(r"\b0\.([0-7]{1,8})\b", q))
    exact = [r for r in rows if r["id"] in ids or (r["kind"] == "game" and r["payload"].get("code") in codes)]
    w = _words(q)
    scored = []
    if w:
        for r in rows:
            s = len(w & r["_w"])
            if s:
                scored.append((s + (0.5 if r["status"] == "proved" else 0), r))
        scored.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for r in exact + [r for _, r in scored]:
        if r["id"] not in seen and len(out) < k + len(exact):
            seen.add(r["id"])
            out.append(r)
    return out


def context_for(q: str, emit=None) -> tuple[str, list[dict]]:
    claims = claim_hits(q)
    lines = [overview()] + kb_hits(q, emit=emit)
    for c in claims:
        nov = f"; novelty: {c['novelty']}" if c.get("novelty") else ""
        lines.append(f"- [Euresis {c['kind']} claim {c['id']}] status: {c['status']} ({label(c)}{nov}) — {c['statement']}")
    return "\n".join(lines), claims


def claim_card(c: dict) -> dict:
    return {"id": c["id"], "kind": c["kind"], "statement": c["statement"], "status": c["status"],
            "label": label(c), "novelty": c.get("novelty") or "", "verifier": c.get("verifier") or ""}


def discoveries(per_category: int = 4) -> list[dict]:
    """Latest gate-verified results from the discovery logs, a few per subject, newest first."""
    reg = {r["id"]: r for r in claims_index()}
    out = []
    for name, cat in CATEGORY.items():
        p = SPACE / name
        if not p.exists():
            continue
        found = []
        for line in reversed(p.read_text(errors="replace").splitlines()[-4000:]):
            m = LOG_LINE.match(line)
            if not m:
                continue
            when, tag, _, text, cid = m.groups()
            c = reg.get(cid)
            if c is None or c["status"] in ("refuted", "unverified", "candidate"):
                continue
            found.append({"when": when, "category": cat, "tag": tag, "text": re.sub(r"\s+", " ", text)[:240],
                          **claim_card(c)})
            if len(found) >= per_category:
                break
        out += found
    out.sort(key=lambda d: d["when"], reverse=True)
    return out


def daemon_running() -> bool:
    for pid in os.listdir("/proc") if os.path.isdir("/proc") else []:
        if pid.isdigit():
            try:
                cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ")
            except OSError:
                continue
            if b"euresis daemon" in cmd:
                return True
    return False


def backend() -> str:
    from . import llm, local_llm
    from .agent import ReasoningCore
    if llm.available() and ReasoningCore._has_credentials():
        return "Claude"
    if local_llm.available():
        return f"local {local_llm.info()['name']}"
    return "offline"


def status() -> dict:
    st = Registry().stats()
    from .lm.model import EuresisLM
    return {"backend": backend(), "daemon": daemon_running(), "claims": st,
            "laws_by": "Euresis-LM + word matching" if EuresisLM.available() else "word matching",
            "fake": bool(os.environ.get("EURESIS_CHAT_FAKE"))}


# ------------------------------------------------------------------ answering
def _history(messages: list[dict], budget: int = 6000) -> list[dict]:
    """The last turns of the conversation that fit in a character budget (newest kept)."""
    out, used = [], 0
    for m in reversed(messages[:-1]):
        t = str(m.get("content", ""))[:3000]
        if used + len(t) > budget:
            break
        out.append({"role": "assistant" if m.get("role") == "assistant" else "user", "content": t})
        used += len(t)
    return list(reversed(out))


def ask(messages: list[dict], emit) -> None:
    q = str(messages[-1]["content"])
    ctx, claims = context_for(q, emit)
    for c in claims[:6]:
        emit({"type": "claim", "claim": claim_card(c), "source": "context"})
    content = f"<knowledge>\n{ctx}\n</knowledge>\n\n{q}"
    turns = _history(messages) + [{"role": "user", "content": content}]
    allowed, written = set(CLAIM_ID.findall(ctx)), []
    raw_emit = emit

    def emit(ev):                                       # keep the reply text for the citation check below
        if ev.get("type") == "token":
            written.append(ev["text"])
        raw_emit(ev)
    try:
        _answer(turns, claims, emit)
    finally:
        reply = "".join(written)
        bad = sorted(set(CLAIM_ID.findall(reply)) - allowed)
        if not claims and STATUS_WORDS.search(reply):    # a gate status with no gate result behind it
            raw_emit({"type": "token", "text": "\n\n> **Status check:** Euresis' verification gate supplied no results "
                      "for this question, so any proved / verified status mentioned above does not come from Euresis."})
        if bad:       # a cited id Euresis did not supply for this question: say so instead of letting it stand
            raw_emit({"type": "token", "text": "\n\n> **Citation check:** " + ", ".join(f"`{b}`" for b in bad) +
                      (" is" if len(bad) == 1 else " are") + " not among the results Euresis supplied for this "
                      "question, so that citation is not supported; ignore it."})


def _answer(turns, claims, emit):
    if os.environ.get("EURESIS_CHAT_FAKE"):            # UI testing without loading a model
        emit({"type": "backend", "name": "test backend"})
        for w in re.findall(r"\S+\s*", "This is a test reply (EURESIS_CHAT_FAKE is set). Relevant verified results "
                                          "are shown above as cards.\n\n- proved claims are machine-checked\n- "
                                          "empirical findings are evidence, not proof"):
            emit({"type": "token", "text": w})
            time.sleep(0.02)
        return
    b = backend()
    emit({"type": "backend", "name": b})
    if b == "Claude":
        return _ask_claude(turns, emit)
    if b.startswith("local"):
        return _ask_local(turns, emit)
    lines = ["No language model is available here (set ANTHROPIC_API_KEY, or run `python -m euresis local "
             "download`), so here is what Euresis knows that matches your question:\n"]
    lines += [f"- **{c['status']}** ({label(c)}) — {c['statement']} `[{c['id']}]`" for c in claims] or ["- nothing matched"]
    emit({"type": "token", "text": "\n".join(lines)})


def _ask_claude(turns, emit):
    import anthropic
    from .llm import MODEL
    with anthropic.Anthropic().beta.messages.stream(
            model=MODEL, max_tokens=16000, system=ASK_SYSTEM, messages=turns,
            thinking={"type": "adaptive"}, output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default") as stream:
        for text in stream.text_stream:
            emit({"type": "token", "text": text})


def ensure_local(emit, wait_s: float = 240):
    """Load the local model, first waiting for the discovery daemon to hand over its copy (it checks the chat
    marker between rounds and frees the memory): two copies do not fit in memory."""
    from . import local_llm
    local_llm.touch_chat()
    if local_llm.loaded():
        return local_llm.load()
    t0, told = time.time(), False
    while local_llm.mem_available_gb() < local_llm.mem_needed_gb() and time.time() - t0 < wait_s:
        if not told:
            emit({"type": "step", "text": "waiting for the discovery daemon to hand over the model memory…"})
            told = True
        time.sleep(3)
        local_llm.touch_chat()
    emit({"type": "step", "text": "loading the local model…"})
    return local_llm.load(log=lambda *a: None)


def _idle_unloader():
    from . import local_llm
    while True:
        time.sleep(60)
        if local_llm.loaded() and not MODEL_LOCK.locked() and time.time() - _LAST_USE[0] > IDLE_UNLOAD_MIN * 60:
            with MODEL_LOCK:
                local_llm.unload()


def _ask_local(turns, emit):
    from . import local_llm
    llm = ensure_local(emit)
    prompt = local_llm.render(ASK_SYSTEM, turns, None, think=False)
    while len(llm.tokenize(prompt.encode())) > llm.n_ctx() - 1300 and len(turns) > 1:
        turns = turns[1:]                               # drop the oldest turns if the context is full
        prompt = local_llm.render(ASK_SYSTEM, turns, None, think=False)
    for chunk in llm.create_completion(prompt, max_tokens=1200, temperature=0.6, top_p=0.95, top_k=20,
                                       stop=["<|im_end|>", "<|endoftext|>"], stream=True):
        emit({"type": "token", "text": chunk["choices"][0]["text"]})


def research(messages: list[dict], emit) -> None:
    q = str(messages[-1]["content"])
    if os.environ.get("EURESIS_CHAT_FAKE"):
        emit({"type": "backend", "name": "test backend"})
        for s in ["[1] model: 1600 prompt + 40 new tokens in 0.1 s", "    submit_claim({\"kind\": \"z3\", …})"]:
            emit({"type": "step", "text": s})
            time.sleep(0.2)
        c = claim_hits("damped oscillator quality factor", 1)
        if c:
            emit({"type": "claim", "claim": claim_card(c[0]), "source": "research"})
        emit({"type": "token", "text": "## Report\n\nTest report: claims above were decided by the gate."})
        return
    from .agent import ReasoningCore
    from .cli import _load
    from .space import ThoughtSpace
    if "loaded" not in _CACHE:
        emit({"type": "step", "text": "loading Euresis' knowledge base and concept model…"})
        _CACHE["loaded"] = _load()
    kb, eng, model = _CACHE["loaded"]
    reg = Registry()
    shown, box = set(), {}

    def log(*parts):
        emit({"type": "step", "text": " ".join(str(p) for p in parts)})
        for cid in getattr(box.get("core"), "session_claims", []):   # stream each claim once the gate decides it
            c = reg.get(cid)
            if c and (cid, c["status"]) not in shown:
                shown.add((cid, c["status"]))
                emit({"type": "claim", "claim": claim_card(c), "source": "research"})

    core = box["core"] = ReasoningCore(kb, eng, model, ThoughtSpace(), registry=reg, log=log)
    backend_pref = "claude" if backend() == "Claude" else "local"
    emit({"type": "backend", "name": backend()})
    if backend_pref == "local":
        ensure_local(emit)
    report = core.research(q, backend=backend_pref)
    log("gate decisions collected")
    if report:
        path = core.save_report(report)
        emit({"type": "token", "text": report})
        emit({"type": "step", "text": f"report saved to {path.relative_to(ROOT)}"})
    else:
        why = getattr(core, "ended", None) or "no language model was reachable"
        emit({"type": "token", "text": f"No report: {why}. Nothing was claimed."})


# ------------------------------------------------------------------ website (GitHub Pages)
SITE_DIR = ROOT / "site"
ASSETS = ("logo.png", "logo-dark.png", "mark.png", "mark-dark.png", "favicon.png")


def site_data() -> dict:
    """Everything the published chat needs to answer in the browser: every claim with its gate status and label
    (solved octal games packed as [code, pre-period, period, id]), the knowledge-base laws, the latest results."""
    from .games import KNOWN_GAMES
    rows = claims_index(max_age=0)
    games, claims, game_novelty = [], [], ""
    for r in rows:
        pl = r.get("payload") or {}
        if r["kind"] == "game" and r["status"] == "proved" and pl.get("code") not in KNOWN_GAMES:
            games.append([pl["code"], int(pl["preperiod"]), int(pl["period"]), r["id"]])
            game_novelty = game_novelty or (r.get("novelty") or "")
        else:
            claims.append({"id": r["id"], "kind": r["kind"], "status": r["status"], "label": label(r),
                           "novelty": r.get("novelty") or "", "verifier": r.get("verifier") or "",
                           "statement": r["statement"][:500]})
    kb, _ = _kb()
    laws = [{"name": f.name, "eq": f.pretty()} for f in kb.formulas]
    return {"updated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "stats": Registry().stats(),
            "games": games, "game_novelty": game_novelty or "unchecked", "claims": claims, "laws": laws,
            "discoveries": discoveries()}


def export_site(log=print) -> Path:
    """Publish the chat as the website's front page (index.html at the repository root, served by GitHub Pages)
    with its data in site/. The page answers by searching that data; it has no language model."""
    from .registry import atomic_write
    SITE_DIR.mkdir(exist_ok=True)
    atomic_write(SITE_DIR / "data.json", json.dumps(site_data(), ensure_ascii=False, separators=(",", ":")))
    html = (WEB / "index.html").read_text()
    for a in ASSETS:
        html = html.replace(f'"/{a}"', f'"euresis/web/{a}"')
    html = html.replace("<script>", '<script>window.EURESIS_SITE = { data: "site/data.json" };</script>\n<script>', 1)
    atomic_write(ROOT / "index.html", html)
    log(f"website updated: index.html + site/data.json ({(SITE_DIR / 'data.json').stat().st_size // 1024} KB)")
    return ROOT / "index.html"


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "EuresisChat/1.0"
    STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/logo.png": ("logo.png", "image/png"),
              "/logo-dark.png": ("logo-dark.png", "image/png"), "/mark.png": ("mark.png", "image/png"),
              "/mark-dark.png": ("mark-dark.png", "image/png"), "/favicon.png": ("favicon.png", "image/png")}

    def log_message(self, fmt, *args):                  # quiet: no per-request lines
        pass

    def _send(self, code: int, body: bytes, ctype: str, cache: bool = False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in self.STATIC:
            name, ctype = self.STATIC[path]
            return self._send(200, (WEB / name).read_bytes(), ctype, cache=name.endswith(".png"))
        if path == "/space/space.html" and (SPACE / "space.html").exists():
            return self._send(200, (SPACE / "space.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/status":
            return self._json(status())
        if path == "/api/discoveries":
            return self._json(discoveries())
        m = re.fullmatch(r"/api/claim/([a-z]{3}-[0-9a-f]{12})", path)
        if m:
            c = Registry().get(m.group(1))
            return self._json({**claim_card(c), "payload": c.get("payload"), "evidence": c.get("evidence")}
                              if c else {"error": "no such claim"}, 200 if c else 404)
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/api/chat":
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 1_000_000:
            return self._json({"error": "request too large"}, 413)
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
            messages = [m for m in req["messages"] if str(m.get("content", "")).strip()]
            assert messages and messages[-1].get("role") == "user"
        except Exception:
            return self._json({"error": "expected {messages: [..., {role: 'user', content}], mode}"}, 400)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        write_lock = threading.Lock()

        def emit(ev):                                    # raises if the browser went away → generation stops
            with write_lock:
                self.wfile.write(f"data: {json.dumps(ev, default=str)}\n\n".encode())
                self.wfile.flush()

        t0 = time.time()
        try:
            if not MODEL_LOCK.acquire(blocking=False):
                emit({"type": "step", "text": "waiting: another chat is using the model…"})
                MODEL_LOCK.acquire()
            try:
                (research if req.get("mode") == "research" else ask)(messages, emit)
            finally:
                _LAST_USE[0] = time.time()
                MODEL_LOCK.release()
            emit({"type": "done", "seconds": round(time.time() - t0, 1)})
        except (BrokenPipeError, ConnectionResetError):
            pass                                         # the user pressed stop or closed the tab
        except Exception as e:                           # shown in the chat, not hidden
            try:
                emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
            except OSError:
                pass


def serve(host: str = "127.0.0.1", port: int = 8765, log=print) -> None:
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=lambda: (claims_index(), euresis_lm(), kb_hits("warm up")), daemon=True).start()   # first reply fast
    threading.Thread(target=_idle_unloader, daemon=True).start()
    log(f"Euresis Chat on http://{host}:{port}  (backend: {backend()}; Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
