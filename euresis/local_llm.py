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
MODEL_FILE = "Qwen3-14B-Q4_K_M.gguf"
MODEL_URL = "https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/main/" + MODEL_FILE
MODEL_INFO = {"name": "Qwen3-14B", "parameters": "14.8 B", "quantisation": "Q4_K_M (4-bit)", "size_gb": 9.0,
              "license": "Apache-2.0", "source": "https://huggingface.co/Qwen/Qwen3-14B-GGUF"}

_LLM = None


def model_path() -> Path:
    return Path(os.environ.get("EURESIS_LOCAL_MODEL", MODEL_DIR / MODEL_FILE))


def available() -> bool:
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    p = model_path()
    return p.exists() and p.stat().st_size > 8_000_000_000


def download(log=print) -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    out = MODEL_DIR / MODEL_FILE
    log(f"downloading {MODEL_INFO['name']} ({MODEL_INFO['size_gb']} GB) → {out}")
    subprocess.run(["curl", "-L", "-C", "-", "--retry", "5", "-o", str(out), MODEL_URL], check=True)
    return out


def load(n_ctx: int = 12288, log=print):
    """Load once per process (about 10–30 s); later calls reuse it."""
    global _LLM
    if _LLM is None:
        from llama_cpp import Llama
        t0 = time.time()
        _LLM = Llama(model_path=str(model_path()), n_ctx=n_ctx, n_threads=os.cpu_count() or 4,
                     n_batch=512, verbose=False)
        log(f"loaded {MODEL_INFO['name']} in {time.time() - t0:.0f} s")
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
