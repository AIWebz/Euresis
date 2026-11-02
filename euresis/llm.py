"""Optional language backend: Claude, grounded in Euresis' own knowledge.

Euresis works fully offline. If the `anthropic` package is installed and
credentials are available (ANTHROPIC_API_KEY or an `ant auth login` profile),
`euresis ask` additionally sends the retrieved laws, Euresis' derivations and
the question to Claude for a written explanation.
"""
from __future__ import annotations

MODEL = "claude-opus-5-5"

SYSTEM = (
    "You are the language interface of Euresis, a scientific discovery engine. "
    "Answer using the supplied knowledge-base excerpts and Euresis' derived results. "
    "Show the governing equations, keep units consistent, state assumptions, and say "
    "clearly when something is a hypothesis rather than established science."
)


def available() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def ask(question: str, context: str) -> str | None:
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": f"<knowledge>\n{context}\n</knowledge>\n\nQuestion: {question}"}],
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        return None
    except TypeError:   # no credentials configured
        return None
    except anthropic.APIConnectionError:
        return None
    except anthropic.APIStatusError as e:
        return f"(Claude backend error {e.status_code}; showing offline answer only)"
    if msg.stop_reason == "refusal":
        return "(The language backend declined this request.)"
    return "".join(b.text for b in msg.content if b.type == "text") or None
