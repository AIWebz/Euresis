"""The Euresis reasoning core: a frontier language model (Claude) with verified tools.

Claude does the open-ended thinking — reading, connecting ideas across fields,
designing derivations and experiments. It never has to be trusted on facts it
can check: every quantitative or formal claim is routed to a tool that cannot
make mistakes in its own domain, and every idea is checked against the
published literature before it may be called new.

    knowledge   search_knowledge      Euresis' laws, principles, constants, own past results
    literature  search_literature     arXiv · PubMed · Semantic Scholar · OpenAlex + local index
                check_novelty         is this already published?
    exact maths computer_algebra      SymPy: simplify, solve, diff, integrate, series, limits
                check_dimensions      Euresis' dimensional analysis on any equation
                prove                 Z3 theorem prover (proof or counterexample)
                check_lean            Lean 4 proof checker (when installed)
    simulation  simulate              physics / chemistry / climate models
                run_experiment        parameter sweep → dataset → law search
    code        run_python            sandboxed Python (numpy, scipy, sympy; no network)
    memory      record_idea           verified + novelty-checked idea → Thought Space

Everything Claude does is written to the Thought Space.
"""
from __future__ import annotations

import json

from . import literature, simulate, verify
from .connect import IdeaEngine
from .discover import search_forms, Dataset
from .engine import Engine
from .explorer import DIRECTIVE
from .kb import KnowledgeBase
from .model import TextRetriever
from .space import ThoughtSpace

MODEL = "claude-opus-5-5"

SYSTEM = f"""You are the reasoning core of Euresis, a scientific discovery system.

Standing directive: {DIRECTIVE}

How you work:
- Start from what is established: search Euresis' knowledge and the literature before theorising.
- Look for connections — a law, mechanism or mathematical structure in one field that bears on
  another — and build new ideas from them.
- Never assert a quantitative or formal claim you have not checked with a tool: use
  computer_algebra / check_dimensions for algebra and units, prove or check_lean for mathematical
  statements, simulate / run_experiment / run_python for numbers.
- Before calling anything new, run check_novelty. Report its verdict honestly; "no close match"
  is not proof of novelty, and an unreachable literature source means novelty is unchecked.
- Record every idea worth keeping with record_idea (Euresis verifies it again independently).
- Finish with a concise report: question, what you established (with the tool evidence), ideas
  (each with verification status, novelty verdict, prediction and test), and open problems.
  Clearly separate established facts, verified-but-untested ideas, and speculation."""


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


TOOLS = [
    {"name": "search_knowledge", "description": "Search Euresis' knowledge base (laws, principles, constants) "
     "and its own previous results in the Thought Space.",
     "input_schema": _schema({"query": {"type": "string"}}, ["query"])},
    {"name": "search_literature", "description": "Search published papers (arXiv, PubMed, Semantic Scholar, "
     "OpenAlex) and the local paper index. Returns titles, years, abstracts, links, and which sources responded.",
     "input_schema": _schema({"query": {"type": "string"}, "max_results": {"type": "integer"}}, ["query"])},
    {"name": "check_novelty", "description": "Check whether an idea is already published. Returns a verdict, "
     "the closest papers and their similarity, and which sources were searched.",
     "input_schema": _schema({"statement": {"type": "string"},
                              "keywords": {"type": "array", "items": {"type": "string"}}}, ["statement"])},
    {"name": "computer_algebra", "description": "Exact symbolic maths with SymPy. operation: simplify | solve | "
     "diff | integrate | limit | series | equal (expression 'a == b').",
     "input_schema": _schema({"operation": {"type": "string"}, "expression": {"type": "string"},
                              "variable": {"type": "string"}, "point": {"type": "string"},
                              "order": {"type": "integer"}}, ["operation", "expression"])},
    {"name": "check_dimensions", "description": "Check an equation for dimensional consistency and whether it "
     "is already a known law. Map every symbol to a quantity id (e.g. mass, velocity, energy) or declare a new "
     "quantity with its SI dimension like 'M L2 T-2'. Constants (G, c, h, hbar, k_B, e, epsilon_0, mu_0, ...) "
     "need no mapping.",
     "input_schema": _schema({"equation": {"type": "string"}, "variables": {"type": "array", "items": _schema(
         {"symbol": {"type": "string"}, "quantity_id": {"type": "string"},
          "new_quantity_dimension": {"type": "string"}}, ["symbol", "quantity_id"])}}, ["equation", "variables"])},
    {"name": "prove", "description": "Prove a mathematical claim with the Z3 theorem prover, or get a "
     "counterexample. variables maps names to Real | Int | Bool; claim and assumptions use Python syntax with "
     "And, Or, Not, Implies.",
     "input_schema": _schema({"claim": {"type": "string"}, "variables": {"type": "object"},
                              "assumptions": {"type": "array", "items": {"type": "string"}}}, ["claim"])},
    {"name": "check_lean", "description": "Type-check a Lean 4 source file; success means its theorems are proved.",
     "input_schema": _schema({"source": {"type": "string"}}, ["source"])},
    {"name": "simulate", "description": "Run a numerical model. Models and parameters: pendulum(length,g,theta0,"
     "damping) · orbit(mass,r0,v_factor) · projectile(v0,angle_deg,g,drag_per_mass) · oscillator(mass,k,damping,"
     "force,drive_freq) · rlc(R,L,C,V0) · heat1d(length,diffusivity,t_end) · kinetics(reactions,rate_constants,"
     "initial,t_end) · arrhenius(A,Ea,temperatures) · ebm(co2_ppm,years,ice_albedo_feedback). SI units.",
     "input_schema": _schema({"model": {"type": "string"}, "params": {"type": "object"}}, ["model"])},
    {"name": "run_experiment", "description": "Sweep a simulator over parameter values, measure an output, and "
     "search the resulting dataset for the law relating them (power laws, exponentials, reciprocals).",
     "input_schema": _schema({"model": {"type": "string"}, "vary": {"type": "object"},
                              "measure": {"type": "string"}, "fixed": {"type": "object"}},
                             ["model", "vary", "measure"])},
    {"name": "find_law", "description": "Physics-informed symbolic regression: give data columns with their SI "
     "dimensions (e.g. 'M L2 T-2'; '1' for dimensionless) and the target column; returns the exact equation if one "
     "exists in Euresis' search space (dimensional analysis + functional-form search + constant identification).",
     "input_schema": _schema({"columns": {"type": "object", "description": "name -> {values: [...], dimension: str}"},
                              "target": {"type": "string"},
                              "noise": {"type": "number", "description": "expected relative measurement error, e.g. 0.01"}},
                             ["columns", "target"])},
    {"name": "run_python", "description": "Execute Python in a sandbox (numpy, scipy, sympy; no network; 60 s). "
     "Print what you need.", "input_schema": _schema({"code": {"type": "string"}}, ["code"])},
    {"name": "record_idea", "description": "Record an idea in the Thought Space. Euresis re-verifies the equation "
     "and checks the literature before storing it.",
     "input_schema": _schema({
         "title": {"type": "string"}, "statement": {"type": "string"}, "equation": {"type": "string"},
         "variables": {"type": "array", "items": _schema({"symbol": {"type": "string"},
                                                          "quantity_id": {"type": "string"},
                                                          "new_quantity_dimension": {"type": "string"}},
                                                         ["symbol", "quantity_id"])},
         "builds_on": {"type": "array", "items": {"type": "string"}},
         "fields": {"type": "array", "items": {"type": "string"}},
         "prediction": {"type": "string"}, "test": {"type": "string"},
         "novelty_claim": {"type": "string"}},
        ["title", "statement", "equation", "variables", "prediction", "test"])},
]


class ReasoningCore:
    def __init__(self, kb: KnowledgeBase, engine: Engine, model, space: ThoughtSpace | None, log=print):
        self.kb, self.E, self.model, self.space, self.log = kb, engine, model, space, log
        self.retriever = TextRetriever(kb.documents())
        self.ideas = IdeaEngine(kb, engine, model, space, log=lambda *a: None)
        self.qid = None

    # ------------------------------------------------------------- tools
    def execute(self, name: str, args: dict) -> dict:
        if name == "search_knowledge":
            hits = [{"kind": d[0], "title": d[1], "text": d[2][:400], "score": round(s, 3)}
                    for d, s in self.retriever.search(args["query"], 8)]
            own = []
            if self.space is not None:
                words = [w for w in args["query"].lower().split() if len(w) > 4]
                own = [{"kind": t["kind"], "title": t["title"], "formula": t["formula"], "status": t["status"]}
                       for t in self.space.thoughts.values()
                       if t["kind"] in ("idea", "data_discovery", "scale", "prediction", "hypothesis")
                       and any(w in (t["title"] + t["body"]).lower() for w in words)][:6]
            return {"knowledge": hits, "euresis_results": own}
        if name == "search_literature":
            papers, status = literature.search(args["query"], int(args.get("max_results", 8)))
            return {"sources": status, "papers": [{"title": p.title, "year": p.year, "source": p.source,
                                                   "url": p.url, "abstract": p.abstract[:600]} for p in papers[:12]]}
        if name == "check_novelty":
            r = literature.novelty(args["statement"], args.get("keywords"))
            r["closest"] = [{k: c[k] for k in ("similarity", "title", "year", "url")} for c in r["closest"]]
            return r
        if name == "computer_algebra":
            return verify.cas(args["operation"], args["expression"], args.get("variable", ""),
                              args.get("point", ""), int(args.get("order", 6)))
        if name == "check_dimensions":
            v = [dict(new_quantity_dimension="", **x) for x in args["variables"]]
            res = self.ideas.verify({"equation": args["equation"], "variables": v})
            return {"ok": res["ok"], "checks": res["checks"], "known_as": res.get("known")}
        if name == "prove":
            return verify.prove_z3(args["claim"], args.get("variables"), args.get("assumptions"))
        if name == "check_lean":
            return verify.check_lean(args["source"])
        if name == "simulate":
            return simulate.run(args["model"], **(args.get("params") or {}))
        if name == "run_experiment":
            exp = simulate.experiment(args["model"], args["vary"], args["measure"], args.get("fixed"))
            cols = exp["columns"]
            ds = Dataset("experiment", f"simulated {args['model']}", "Euresis simulator",
                         {c: c for c in cols}, {c: [r[c] for r in exp["rows"]] for c in cols}, args["measure"])
            forms = search_forms(ds)[:3]
            return {"rows": exp["rows"][:40], "best_fits": json.loads(json.dumps(forms, default=float))}
        if name == "find_law":
            import numpy as np
            from .dimensions import D
            from .sr import regress
            cols = args["columns"]
            names = [c for c in cols if c != args["target"]]
            X = np.array([cols[c]["values"] for c in names], float).T
            y = np.array(cols[args["target"]]["values"], float)
            r = regress(X, y, [D(cols[c]["dimension"]) for c in names], D(cols[args["target"]]["dimension"]), names,
                        noise=float(args.get("noise", 0.0)))
            if r is None:
                return {"found": False}
            return {"found": True, "equation": f"{args['target']} = {r['expr']}", "exact": r["exact"],
                    "relative_error": r["val_err"], "pi_groups": r["pi_groups"], "form": r["family"]}
        if name == "run_python":
            return verify.run_python(args["code"])
        if name == "record_idea":
            idea = dict(args)
            idea["variables"] = [dict(new_quantity_dimension="", **x) for x in args.get("variables", [])]
            idea.setdefault("builds_on", [])
            idea.setdefault("fields", [])
            res = self.ideas.verify(idea)
            nov = literature.novelty(idea["statement"] + " " + idea.get("title", ""), idea.get("fields"))
            res["checks"].append(f"literature: {nov['verdict']}")
            tid = self.ideas.record(res, self.qid)
            return {"recorded": tid, "verified": res["ok"], "checks": res["checks"],
                    "closest_papers": [{k: c[k] for k in ("similarity", "title", "year")} for c in nov["closest"][:3]]}
        return {"error": f"unknown tool {name}"}

    def _note(self, name, args, result):
        if self.space is None or name in ("record_idea",):
            return
        status = "ok"
        if isinstance(result, dict):
            status = result.get("status") or ("error" if "error" in result else "ok")
        self.space.add("evidence", f"{name}: {json.dumps(args)[:90]}", body=json.dumps(result, default=str)[:1500],
                       domain="method", parents=[self.qid] if self.qid else [], status=f"tool result · {status}",
                       score=0.3)

    # -------------------------------------------------------------- loop
    def research(self, question: str, max_turns: int = 30) -> str | None:
        try:
            import anthropic
        except ImportError:
            self.log("The `anthropic` package is not installed: pip install anthropic")
            return None
        if self.space is not None:
            self.qid = self.space.add("question", question, status="research question", domain="method",
                                      body="Investigated by the reasoning core.", score=1.0)
        client = anthropic.Anthropic() if self._has_credentials() else None
        if client is None:
            self.log("No Claude credentials: set ANTHROPIC_API_KEY or run `ant auth login`.")
            return None
        messages = [{"role": "user", "content": question}]
        for turn in range(max_turns):
            try:
                resp = client.beta.messages.create(
                    model=MODEL, max_tokens=16000, system=SYSTEM, tools=TOOLS, messages=messages,
                    thinking={"type": "adaptive"}, output_config={"effort": "high"},
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            except anthropic.AuthenticationError:
                self.log("Claude rejected the credentials.")
                return None
            except anthropic.RateLimitError:
                self.log("Rate limited by the Claude API; try again shortly.")
                return None
            except anthropic.APIStatusError as e:
                self.log(f"Claude API error {e.status_code}: {e.message}")
                return None
            except anthropic.APIConnectionError:
                self.log("Cannot reach the Claude API (network policy?).")
                return None
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "refusal":
                self.log("The model declined this request.")
                return None
            if resp.stop_reason == "pause_turn":
                continue
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                if resp.stop_reason == "max_tokens":
                    messages.append({"role": "user", "content": "Continue."})
                    continue
                text = "".join(b.text for b in resp.content if b.type == "text")
                if self.space is not None:
                    self.space.add("insight", f"Research report: {question[:80]}", body=text[:6000],
                                   domain="method", parents=[self.qid], status="reasoning-core report", score=1.0)
                return text
            results = []
            for c in calls:
                self.log(f"  [{turn + 1}] {c.name}({json.dumps(c.input)[:110]})")
                try:
                    out = self.execute(c.name, c.input)
                    err = False
                except Exception as e:     # tool failure is reported to the model, not hidden
                    out, err = {"error": f"{type(e).__name__}: {e}"}, True
                self._note(c.name, c.input, out)
                results.append({"type": "tool_result", "tool_use_id": c.id,
                                "content": json.dumps(out, default=str)[:20000], "is_error": err})
            messages.append({"role": "user", "content": results})
        self.log("Stopped after the maximum number of turns.")
        return None

    @staticmethod
    def _has_credentials() -> bool:
        import os
        from pathlib import Path
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                    or (Path.home() / ".config" / "anthropic").exists())
