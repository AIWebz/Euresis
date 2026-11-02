"""Idea engine: Claude proposes connections, Euresis verifies them.

Euresis finds *connection points* in its knowledge — laws from different fields
that share quantities, frontier problems and the laws that touch them, its own
best candidate results — and asks Claude to propose new ideas that build on
them. Every idea comes back as structured data (an equation plus the meaning of
every symbol). Euresis then checks each idea itself:

* the equation parses and every symbol maps to a known quantity or constant;
* it is dimensionally consistent;
* it is not already a law in the knowledge base (if it is, it is marked known);
* the laws it claims to build on exist.

Only then is it written into the Thought Space, linked to what it builds on.
An idea passing these checks is *well-formed and consistent*, not *true* —
each carries the test Claude proposed so it can be checked against experiment.

Requires the `anthropic` package and credentials (ANTHROPIC_API_KEY or an
`ant auth login` profile). Without them, Euresis still lists the connection
points it would ask about, as open questions in the Thought Space.
"""
from __future__ import annotations

import json
import random
import re
from itertools import combinations

import sympy as sp

from .engine import Engine, Relation
from .kb import FUNCS, DimensionError, KnowledgeBase, dim_of, family
from .space import ThoughtSpace

MODEL = "claude-opus-5-5"

AREA = {"chemistry": "chemistry", "biology": "life", "earth_science": "earth", "astrophysics": "space",
        "astronomy": "space", "gravitation": "space", "information": "information", "mathematics": "math",
        "geometry": "math", "method": "math"}


def area(domain: str) -> str:
    return AREA.get(domain, "physics")

SYSTEM = (
    "You are the idea generator inside Euresis, a scientific discovery engine. You receive excerpts "
    "of established science that Euresis has identified as connection points. Your job: take in that "
    "information and propose NEW ideas that connect these pieces to each other and to prior knowledge — "
    "relations, mechanisms or predictions that would extend what is known. Rules: build explicitly on the "
    "supplied laws; prefer ideas that bridge different fields; every idea must have a concrete equation "
    "in SymPy syntax and a falsifiable test; use only the quantity ids and constant symbols listed (or "
    "declare a new quantity with its SI dimension); be honest about novelty — if an idea is already "
    "known in the literature, say so in novelty_claim; never present speculation as established fact."
)

IDEA_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "statement": {"type": "string"},
                    "equation": {"type": "string", "description": "SymPy syntax with '=', e.g. 'T = 2*pi*sqrt(L/g)'"},
                    "variables": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string"},
                                "quantity_id": {"type": "string"},
                                "new_quantity_dimension": {"type": "string",
                                                           "description": "only if quantity_id is new, e.g. 'M L2 T-2'"},
                            },
                            "required": ["symbol", "quantity_id", "new_quantity_dimension"],
                            "additionalProperties": False,
                        },
                    },
                    "builds_on": {"type": "array", "items": {"type": "string"}},
                    "fields": {"type": "array", "items": {"type": "string"}},
                    "prediction": {"type": "string"},
                    "test": {"type": "string"},
                    "novelty_claim": {"type": "string", "enum": ["likely known", "possibly new", "speculative"]},
                },
                "required": ["title", "statement", "equation", "variables", "builds_on", "fields",
                             "prediction", "test", "novelty_claim"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


class IdeaEngine:
    def __init__(self, kb: KnowledgeBase, engine: Engine, model, space: ThoughtSpace | None, seed=0, log=print):
        self.kb, self.E, self.model, self.space, self.log = kb, engine, model, space, log
        self.rng = random.Random(seed)

    # ------------------------------------------------------ connection points
    def connection_points(self, n=6):
        """Pairs of laws from different fields that share a quantity family, ranked by the
        concept model's plausibility that their *other* quantities are related."""
        by_fam: dict[str, list] = {}
        for f in self.kb.formulas:
            for fam in f.families:
                by_fam.setdefault(fam, []).append(f)
        cands = []
        for fam, laws in by_fam.items():
            if len(laws) > 60:          # ubiquitous (time, length): weak connection points
                continue
            for a, b in combinations(laws, 2):
                if a.domain == b.domain or "geometry" in (a.domain, b.domain):
                    continue
                if a.families <= b.families or b.families <= a.families:   # one restates the other
                    continue
                ext = (a.quantities | b.quantities) - {q for q in a.quantities if family(q) == fam}
                if self.model is not None:
                    qs = sorted(ext)
                    pairs = [(x, y) for x in a.quantities for y in b.quantities if x != y]
                    s = sum(self.model.score(f"q:{x}", f"q:{y}") for x, y in pairs) / max(1, len(pairs))
                else:
                    s = self.rng.random()
                s += 0.5 * (area(a.domain) != area(b.domain))   # favour bridges between distant fields
                cands.append((s, fam, a, b))
        cands.sort(key=lambda c: -c[0])
        out, used = [], set()
        for s, fam, a, b in cands:
            if a.name in used or b.name in used:
                continue
            used |= {a.name, b.name}
            out.append({"shared": fam, "laws": [a, b], "score": s})
            if len(out) >= n:
                break
        return out

    def _context(self, cp) -> str:
        laws = cp["laws"]
        qids = sorted({q for f in laws for q in f.quantities})
        related = []
        if self.model is not None:
            for q in qids[:6]:
                related += [n[2:] for n, _ in self.model.related(f"q:{q}", k=4) if n.startswith("q:")]
        qids = sorted(set(qids) | set(related))
        lines = [f"Connection point: the quantity '{self.kb.qname(cp['shared'])}' appears in both of these "
                 f"laws from different fields:"]
        for f in laws:
            lines.append(f"- [{f.domain}] {f.name}: {f.pretty()}")
        nearby = [g for g in self.kb.formulas if g not in laws and len(g.quantities & set(qids)) >= 2][:8]
        if nearby:
            lines.append("Other established laws nearby in Euresis' knowledge:")
            lines += [f"- [{g.domain}] {g.name}: {g.pretty()}" for g in nearby]
        lines.append("Quantity ids you may use: " + ", ".join(f"{q} ({self.kb.qname(q)}, {self.kb.quantities[q][1]})"
                                                          for q in qids if q in self.kb.quantities))
        lines.append("Constant symbols you may use: " + ", ".join(f"{k} ({v[0]})" for k, v in self.kb.constants.items()))
        return "\n".join(lines)

    # ---------------------------------------------------------- Claude call
    def ask_claude(self, context: str, n_ideas=3) -> list[dict] | None:
        try:
            import anthropic
        except ImportError:
            return None
        client = anthropic.Anthropic()
        prompt = (f"{context}\n\nPropose {n_ideas} new ideas that connect these laws to each other and to prior "
                  f"knowledge. Each idea needs an equation, the meaning of every symbol, the laws it builds on, "
                  f"a prediction and a test.")
        try:
            with client.beta.messages.stream(
                model=MODEL, max_tokens=32000, system=SYSTEM,
                thinking={"type": "adaptive"},
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": IDEA_SCHEMA}},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                msg = stream.get_final_message()
        except anthropic.AuthenticationError:
            self.log("  Claude: no valid credentials")
            return None
        except TypeError:   # no credentials configured
            self.log("  Claude: no credentials configured")
            return None
        except anthropic.APIConnectionError:
            self.log("  Claude: cannot connect")
            return None
        except anthropic.APIStatusError as e:
            self.log(f"  Claude: API error {e.status_code}")
            return None
        if msg.stop_reason == "refusal":
            return []
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            return json.loads(text).get("ideas", [])
        except json.JSONDecodeError:
            return []

    # ----------------------------------------------------------- verification
    def verify(self, idea: dict) -> dict:
        """Euresis' independent check of one proposed idea."""
        res = {"idea": idea, "ok": False, "checks": []}
        eqtxt = idea.get("equation", "")
        if eqtxt.count("=") != 1:
            res["checks"].append("equation must contain exactly one '='")
            return res
        dims = dict(self.kb.dims)
        local, s2q = dict(FUNCS), {}
        from .dimensions import D
        for v in idea.get("variables", []):
            sym, qid = v["symbol"], v["quantity_id"]
            if qid in self.kb.quantities:
                d = self.kb.quantities[qid][1]
            elif v.get("new_quantity_dimension"):
                try:
                    d = D(v["new_quantity_dimension"])
                except (ValueError, ArithmeticError):
                    res["checks"].append(f"bad dimension for new quantity {qid}")
                    return res
                res["checks"].append(f"introduces new quantity '{qid}' [{d}]")
            else:
                res["checks"].append(f"unknown quantity '{qid}'")
                return res
            s = sp.Symbol(qid if qid not in s2q.values() else f"{qid}__{sym}")
            local[sym] = s
            dims[s] = d
            s2q[s] = qid
        for k in self.kb.constants:
            local.setdefault(k, sp.Symbol(k))
        idents = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", eqtxt))
        missing = [i for i in idents if i not in local]
        if missing:
            res["checks"].append(f"undefined symbols: {missing}")
            return res
        try:
            lhs, rhs = eqtxt.split("=")
            eq = sp.Eq(sp.sympify(lhs, locals=local), sp.sympify(rhs, locals=local), evaluate=False)
        except (sp.SympifyError, SyntaxError, TypeError):
            res["checks"].append("equation does not parse")
            return res
        try:
            dl, dr = dim_of(eq.lhs, dims), dim_of(eq.rhs, dims)
        except DimensionError as e:
            res["checks"].append(f"dimensionally inconsistent: {e}")
            return res
        if dl != dr:
            res["checks"].append(f"dimensionally inconsistent: [{dl}] vs [{dr}]")
            return res
        res["checks"].append("dimensionally consistent")
        consts = {x for x in eq.free_symbols if x.name in self.kb.constants}
        rel = Relation(eq, {x: q for x, q in s2q.items() if x in eq.free_symbols}, consts, "idea",
                       [n for n in idea.get("builds_on", []) if self.kb.by_name(n)], idea.get("title", ""))
        known, ratio = self.E.find_known(rel)
        if known is not None:
            res["checks"].append(f"already in knowledge base as '{known.name}'" + ("" if ratio in (1, -1) else f" (×{ratio})"))
            res["known"] = known.name
        missing_laws = [n for n in idea.get("builds_on", []) if not self.kb.by_name(n)]
        if missing_laws:
            res["checks"].append(f"cites laws not in knowledge base: {missing_laws}")
        res.update(ok=True, relation=rel, pretty=self.E.pretty(rel))
        return res

    def record(self, res: dict, question_id: str | None):
        if self.space is None:
            return None
        idea = res["idea"]
        parents = [question_id] if question_id else []
        for n in idea.get("builds_on", []):
            tid = self.space.make_id("law", f"law|{n}")
            if tid in self.space.thoughts:
                parents.append(tid)
        if not res["ok"]:
            status = "rejected by Euresis: " + "; ".join(res["checks"])
        elif res.get("known"):
            status = "verified consistent · already known"
        else:
            status = f"verified consistent · {idea.get('novelty_claim', 'untested')} · needs experimental test"
        body = (f"{idea.get('statement', '')} Prediction: {idea.get('prediction', '')} "
                f"Test: {idea.get('test', '')} Euresis checks: {'; '.join(res['checks'])}.")
        return self.space.add("idea", idea.get("title", "Idea"), body=body,
                              formula=res.get("pretty") or idea.get("equation", ""),
                              domain=(idea.get("fields") or ["physics"])[0], parents=parents, status=status,
                              score=1.2 if res["ok"] and not res.get("known") else 0.4)

    # ------------------------------------------------------------------ run
    def run(self, n_points=6, ideas_per_point=3):
        points = self.connection_points(n_points)
        online = None
        summary = {"points": len(points), "ideas": 0, "verified": 0, "known": 0, "rejected": 0}
        for cp in points:
            a, b = cp["laws"]
            title = f"Connect {a.name} ({a.domain}) with {b.name} ({b.domain})?"
            qid = None
            if self.space is not None:
                qid = self.space.add("question", title, domain=b.domain, status="connection point",
                                     body=f"Both involve {self.kb.qname(cp['shared'])}.",
                                     parents=[self.space.make_id("law", f"law|{a.name}"),
                                              self.space.make_id("law", f"law|{b.name}")], score=cp["score"])
            self.log(f"connection point: {a.name} ↔ {b.name} (shared: {self.kb.qname(cp['shared'])})")
            if online is False:
                continue
            ideas = self.ask_claude(self._context(cp), ideas_per_point)
            if ideas is None:
                online = False
                self.log("  (Claude unavailable — recorded as an open connection question only)")
                continue
            online = True
            for idea in ideas:
                res = self.verify(idea)
                self.record(res, qid)
                summary["ideas"] += 1
                if not res["ok"]:
                    summary["rejected"] += 1
                elif res.get("known"):
                    summary["known"] += 1
                else:
                    summary["verified"] += 1
                self.log(f"  idea: {idea.get('title')} — {'; '.join(res['checks'])}")
        summary["online"] = bool(online)
        return summary
