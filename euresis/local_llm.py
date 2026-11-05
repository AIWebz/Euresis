"""Local language model backend — a 14-billion-parameter open model, no API needed.

Euresis runs Qwen3-14B (Apache-2.0, by the Qwen team) quantised to 4 bits with
llama.cpp on the CPU: about 9 GB of weights, fits in 15 GB of RAM. It is used
exactly like Claude: as the reasoning core that calls Euresis' verified tools.
Nothing it says is trusted — formal claims go through the verification gate.

    python -m euresis local download      # fetch the weights (9.0 GB) into data/models/
    python -m euresis local info
    python -m euresis local chat "question"
    python -m euresis research "question" --backend local

Tool calling uses Qwen3's native format: tool schemas in the system prompt,
calls as <tool_call>{"name": ..., "arguments": {...}}</tool_call>, results returned
as <tool_response>…</tool_response>.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "data" / "models"
CACHE_DIR = ROOT / "data" / "llm_cache"
CHAT_MARK = ROOT / "data" / "chat_active"       # touched by the chat server while people are chatting
MODELS = {
    "8b": {"file": "Qwen3-8B-Q4_K_M.gguf", "name": "Qwen3-8B", "parameters": "8.2 B", "size_gb": 5.0,
           "url": "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf",
           "source": "https://huggingface.co/Qwen/Qwen3-8B-GGUF"},
    "14b": {"file": "Qwen3-14B-Q4_K_M.gguf", "name": "Qwen3-14B", "parameters": "14.8 B", "size_gb": 9.0,
            "url": "https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q4_K_M.gguf",
            "source": "https://huggingface.co/Qwen/Qwen3-14B-GGUF"},
}


def _installed(size: str) -> bool:
    f = MODEL_DIR / MODELS[size]["file"]
    return f.exists() and f.stat().st_size > MODELS[size]["size_gb"] * 0.9e9


def size() -> str:
    """Which local model to use: EURESIS_LOCAL_SIZE (8b | 14b), else the faster 8B if installed, else 14B."""
    want = os.environ.get("EURESIS_LOCAL_SIZE", "").lower()
    if want in MODELS:
        return want
    return "8b" if _installed("8b") else "14b"


def info() -> dict:
    m = MODELS[size()]
    return {"name": m["name"], "parameters": m["parameters"], "quantisation": "Q4_K_M (4-bit)", "size_gb": m["size_gb"],
            "license": "Apache-2.0", "source": m["source"]}


MODEL_INFO = info()            # kept for callers that read it at import time
MODEL_FILE = MODELS[size()]["file"]
MODEL_URL = MODELS[size()]["url"]

_LLM = None


def model_path() -> Path:
    return Path(os.environ.get("EURESIS_LOCAL_MODEL", MODEL_DIR / MODELS[size()]["file"]))


def available() -> bool:
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    p = model_path()
    return p.exists() and p.stat().st_size > 4_000_000_000


def download(which: str | None = None, log=print) -> Path:
    m = MODELS[which or size()]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    out = MODEL_DIR / m["file"]
    log(f"downloading {m['name']} ({m['size_gb']} GB) → {out}")
    subprocess.run(["curl", "-L", "-C", "-", "--retry", "5", "-o", str(out), m["url"]], check=True)
    return out


def mem_available_gb() -> float:
    """Free memory as the kernel reports it (MemAvailable), in GB; inf if unknown."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1e6
    except OSError:
        pass
    return float("inf")


def mem_needed_gb() -> float:
    return MODELS[size()]["size_gb"] + 2.5      # weights + context and compute buffers


def touch_chat():
    try:
        CHAT_MARK.parent.mkdir(parents=True, exist_ok=True)
        CHAT_MARK.touch()
    except OSError:
        pass


def chat_active(minutes: float = 15) -> bool:
    """True while the chat server has been used recently: discovery then runs without the model, so two copies
    of it never compete for memory (two copies do not fit in 15 GB and the kernel kills one)."""
    try:
        return time.time() - CHAT_MARK.stat().st_mtime < minutes * 60
    except OSError:
        return False


def loaded() -> bool:
    return _LLM is not None


def unload():
    """Free the model's memory (it reloads in a few seconds when next needed)."""
    global _LLM
    if _LLM is not None:
        try:
            _LLM.close()
        except Exception:
            pass
        _LLM = None
        import gc
        gc.collect()


def load(n_ctx: int = 12288, log=print):
    """Load once per process; later calls reuse it.
    Speed-up: a disk cache of evaluated prompts, so the long system prompt with the tool list is not re-read on
    every run."""
    global _LLM
    if _LLM is None:
        free, need = mem_available_gb(), mem_needed_gb()
        if free < need:
            raise MemoryError(f"not enough free memory to load {info()['name']} ({free:.1f} GB free, {need:.1f} GB "
                              "needed); another Euresis process is probably using the model")
        from llama_cpp import Llama, LlamaDiskCache
        t0 = time.time()
        # (prompt-lookup decoding was tried: in this llama.cpp version it needs logits for every context position,
        #  ~7.5 GB extra at this context length — more than the machine has — so it is not used)
        _LLM = Llama(model_path=str(model_path()), n_ctx=n_ctx, n_threads=os.cpu_count() or 4, n_batch=512,
                     verbose=False)
        if os.environ.get("EURESIS_NO_PROMPT_CACHE") is None:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _LLM.set_cache(LlamaDiskCache(cache_dir=str(CACHE_DIR / size()), capacity_bytes=3 << 30))
        log(f"loaded {info()['name']} in {time.time() - t0:.0f} s")
    return _LLM


# ------------------------------------------------------------------ prompting
def _tools_block(tools: list[dict]) -> str:
    fns = [json.dumps({"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                         "parameters": t["input_schema"]}}) for t in tools]
    return ("\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\n"
            "You are provided with function signatures within <tools></tools> XML tags:\n<tools>\n"
            + "\n".join(fns) + "\n</tools>\n\nFor each function call, return a json object with function name and "
            "arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n"
            '{"name": <function-name>, "arguments": <args-json-object>}\n</tool_call>')


def render(system: str, messages: list[dict], tools: list[dict] | None, think: bool) -> str:
    """ChatML prompt in Qwen3's format. messages: {role: user|assistant|tool, content: str}."""
    out = f"<|im_start|>system\n{system}{_tools_block(tools) if tools else ''}<|im_end|>\n"
    i = 0
    while i < len(messages):
        m = messages[i]
        if m["role"] == "tool":                 # consecutive tool results go in one user turn
            parts = []
            while i < len(messages) and messages[i]["role"] == "tool":
                parts.append(f"<tool_response>\n{messages[i]['content']}\n</tool_response>")
                i += 1
            out += "<|im_start|>user\n" + "\n".join(parts) + "<|im_end|>\n"
            continue
        out += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
        i += 1
    out += "<|im_start|>assistant\n"
    if not think:
        out += "<think>\n\n</think>\n\n"        # Qwen3's switch for non-thinking mode
    return out


_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def parse(text: str) -> tuple[str, list[dict]]:
    """Split a completion into visible text and tool calls."""
    calls = []
    for m in _CALL.finditer(text):
        try:
            d = json.loads(m.group(1))
            calls.append({"name": d["name"], "arguments": d.get("arguments") or {}})
        except (json.JSONDecodeError, KeyError):
            calls.append({"name": "_invalid", "arguments": {"raw": m.group(1)[:500]}})
    visible = re.sub(r"<think>.*?</think>", "", _CALL.sub("", text), flags=re.S).strip()
    return visible, calls


def complete(system: str, messages: list[dict], tools: list[dict] | None = None, think: bool = False,
             max_tokens: int = 1500, temperature: float = 0.6, log=print) -> dict:
    llm = load(log=log)
    prompt = render(system, messages, tools, think)
    t0 = time.time()
    r = llm.create_completion(prompt, max_tokens=max_tokens, temperature=temperature, top_p=0.95, top_k=20,
                              stop=["<|im_end|>", "<|endoftext|>"])
    text = r["choices"][0]["text"]
    visible, calls = parse(text)
    u = r.get("usage", {})
    return {"raw": text, "text": visible, "calls": calls, "seconds": round(time.time() - t0, 1),
            "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
            "finish": r["choices"][0].get("finish_reason")}


def ask(question: str, context: str = "", system: str | None = None, think: bool = False, log=print) -> str | None:
    if not available():
        return None
    sys_ = system or ("You are the language interface of Euresis, a scientific discovery engine. Answer using the "
                      "supplied knowledge and derived results. Show governing equations, keep units consistent, "
                      "state assumptions, and say clearly when something is a hypothesis.")
    content = (f"<knowledge>\n{context}\n</knowledge>\n\nQuestion: {question}" if context else question)
    return complete(sys_, [{"role": "user", "content": content}], think=think, max_tokens=1200, log=log)["text"]
