"""Question answering from established knowledge, with Euresis' own reasoning on top.

Pipeline for a question:
1. **Find the knowledge** — measured facts, principles and laws relevant to the
   question (word matching + the concept model; the facts' own keywords).
2. **Reason over it** —
   * composition questions: rank the components; if the question names a
     percentage, find which components add up to it;
   * derive more with its laws: evaluate any law connected to the fact whose
     inputs the fact supplies (e.g. the critical density of the universe from
     the expansion rate), then turn fractions into absolute amounts.
3. **Explain** — how we know (evidence principles), what is still unknown (open
   problems), the source of every number, and a confidence label.
"""
from __future__ import annotations

import itertools
import math
import re

from .engine import Engine
from .kb import KnowledgeBase
from .knowledge.facts import FACTS
from .knowledge.frontier import load as load_frontier
from .model import TextRetriever


def _fmt_pct(x):
    return f"{x * 100:.1f}%" if x >= 0.001 else f"{x * 100:.3f}%"


def _fmt(v):
    return f"{v:.3g}" if 1e-3 <= abs(v) < 1e5 else f"{v:.3e}"


class Answerer:
    def __init__(self, kb: KnowledgeBase | None = None, engine: Engine | None = None):
        self.kb = kb or KnowledgeBase()
        self.E = engine or Engine(self.kb)
        self.fact_docs = [("fact", f["id"], f"{f['subject']}. {f['statement']} {f['keywords']} "
                           + " ".join(f["components"])) for f in FACTS]
        self.fact_retr = TextRetriever(self.fact_docs, k=16)
        self.principles = {p.name: p for p in self.kb.principles}
        self.frontier = load_frontier()

    # ------------------------------------------------------------- 1 find
    def find_fact(self, question):
        q = question.lower()
        hits = self.fact_retr.search(q, len(FACTS))
        best = None
        for (kind, fid, text), score in hits:
            f = next(x for x in FACTS if x["id"] == fid)
            overlap = len(set(re.findall(r"[a-z]{4,}", q)) & set(f["keywords"].split()))
            sc = score + 0.15 * overlap
            if best is None or sc > best[0]:
                best = (sc, f)
        return best if best and best[0] > 0.25 else (best[0] if best else 0, None)

    # ----------------------------------------------------------- 2 reason
    @staticmethod
    def explain_percentage(components, pct):
        """Which components add up to the percentage named in the question?"""
        items = list(components.items())
        best = None
        for r in range(1, len(items) + 1):
            for combo in itertools.combinations(items, r):
                s = sum(v for _, v in combo)
                err = abs(s - pct)
                if best is None or err < best[0] - 1e-9:
                    best = (err, combo, s)
        return best

    def derive(self, fact):
        """Evaluate laws connected to the fact using the quantities the fact supplies."""
        out = []
        for name in fact.get("laws", []):
            f = self.kb.by_name(name)
            if f is None or not fact.get("quantities"):
                continue
            missing = [q for q in f.quantities if q not in fact["quantities"]]
            if len(missing) != 1:
                continue
            target = missing[0]
            val = self.E.evaluate(f, target, fact["quantities"])
            if val is None:
                continue
            out.append({"law": name, "equation": f.pretty(), "quantity": target, "value": val,
                        "name": self.kb.qname(target)})
        return out

    # ------------------------------------------------------------ 3 answer
    def answer(self, question: str) -> dict:
        score, fact = self.find_fact(question)
        if fact is None:
            return {"answered": False, "text": "Euresis has no measured facts that answer this question.",
                    "confidence": "none"}
        comps = sorted(fact["components"].items(), key=lambda kv: -kv[1])
        L = [f"**What {fact['subject']} is made of** (source: {fact['source']}):", ""]
        L += [f"- {name}: {_fmt_pct(v)}" for name, v in comps]
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", question)
        reasoning = []
        if m:
            pct = float(m.group(1)) / 100
            err, combo, s = self.explain_percentage(fact["components"], pct)
            parts = " + ".join(f"{n} ({_fmt_pct(v)})" for n, v in combo)
            rest = [n for n, _ in comps if n not in dict(combo)]
            reasoning.append(f"The {m.group(1)}% in the question is {parts} = {_fmt_pct(s)}; "
                             f"the remaining {_fmt_pct(1 - s)} is {', '.join(rest)}.")
        derived = self.derive(fact)
        for d in derived:
            reasoning.append(f"Using its law '{d['law']}' ({d['equation']}) with the measured expansion rate, Euresis "
                             f"computes the {d['name']}: {_fmt(d['value'])} kg/m³.")
            if d["quantity"] == "critical_density":
                mp = self.kb.constants["m_p"][1]
                for name, v in comps:
                    rho = v * d["value"]
                    reasoning.append(f"  → {name}: {_fmt(rho)} kg/m³ ≈ {rho / mp:.2g} proton masses per cubic metre.")
        if reasoning:
            L += ["", "**Euresis' own reasoning:**", ""] + [f"- {r}" if not r.startswith("  ") else r for r in reasoning]
        ev = [self.principles[n] for n in fact.get("evidence", []) if n in self.principles]
        if ev:
            L += ["", "**How we know:**", ""] + [f"- {p.name}: {p.statement}" for p in ev]
        unknown = [prob for dom, prob, tags in self.frontier
                   if any(u.lower().split(":")[0][:20] in prob.lower() for u in fact.get("unknown", []))]
        mystery = fact.get("unexplained_components", [])
        if mystery:
            L += ["", "**Still unknown:** the amounts are measured, but what " + " and ".join(mystery) +
                  " actually are has not been discovered."] + [f"- {u}" for u in unknown]
        elif unknown:
            L += ["", "**Related open problems:**", ""] + [f"- {u}" for u in unknown]
        conf = ("established amounts; the nature of " + " and ".join(mystery) + " is unknown") if mystery \
            else "established (measured)"
        L += ["", f"*Confidence: {conf}.*"]
        return {"answered": True, "fact": fact["id"], "text": "\n".join(L), "derived": derived,
                "reasoning": reasoning, "confidence": conf}
