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
    gate        submit_claim          every claim → claims registry → verification gate
                                      (Z3, SymPy+mpmath, Lean 4, interval arithmetic, …)
    simulation  simulate              physics / chemistry / climate models
                run_experiment        parameter sweep → dataset → law search
    code        run_python            sandboxed Python (numpy, scipy, sympy; no network)
    planning    propose               hypotheses + research plan (recorded, never counted as results)
    memory      record_idea           dimensionally checked hypothesis → Thought Space

Claude proposes; only verifiers decide. Every claim goes into the claims registry
(``registry.py``) and through the verification gate (``gate.py``); its status there
is set by the verifier, never by the model. The final report's claim table is built
from the registry, and every claim id cited in Claude's text is rewritten with its
gated status. A *discovery* is ``gate.is_discovery``: proved AND not known.

Everything Claude does is written to the Thought Space.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import gate, literature, simulate, verify
from .connect import IdeaEngine
from .discover import search_forms, Dataset
from .engine import Engine
from .explorer import DIRECTIVE
from .kb import KnowledgeBase
from .model import TextRetriever
from .registry import ROOT, Registry
from .space import ThoughtSpace

MODEL = "claude-opus-5-5"

SYSTEM = f"""You are the reasoning core of Euresis, a scientific discovery system.

Standing directive: {DIRECTIVE}

Division of labour: you propose hypotheses, plans and claims; Euresis' verifiers decide what is
true. You cannot set the status of any claim, and nothing you write counts as a result unless it
passed the verification gate.

How you work:
1. Start from what is established: search_knowledge and search_literature before theorising.
2. Call propose with your hypotheses (each with how it could be tested) and a short plan.
3. Explore with the scratch tools (computer_algebra, check_dimensions, simulate, run_experiment,
   find_law, run_python). Their outputs are working notes, not results.
4. Every claim you intend to report — a theorem, an inequality, an identity, a constant, a physical
   relation — must be stated exactly and sent through submit_claim. It is written to the claims
   registry and checked by the verifier for its kind; you get back its claim id and the gate's
   status: proved / verified-numeric / refuted / unverified / candidate (queued).
   If you know a claim is an established result, say so in known_as; never pass off a known result
   as new. Refuted and unverified claims are real outcomes: report them, do not hide them.
5. Prefer claims a verifier can actually decide (polynomial real arithmetic for Z3, closed-form
   identities for SymPy). A timeout is "unverified", not evidence either way.

Final report (plain markdown): the question; the plan; then each result cited by its claim id in
square brackets, e.g. [z3-0123456789ab] — Euresis replaces every id with the status the gate
recorded and appends the authoritative claim table. Do not state any status, novelty or
"discovery" yourself beyond what the gate returned. Anything you say without a claim id is
explicitly speculation or background, and must be labelled as such. "No close match in the
literature" is not proof of novelty. Only a claim that is proved AND not known is a discovery."""


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


# kind → payload fields the verifier needs (see gate.py for the verifier behind each kind)
CLAIM_FIELDS = {
    "z3": ("claim",),
    "identity": ("lhs", "rhs"),
    "inequality": ("P", "Q", "k"),
    "physics-relation": ("claim", "symbols"),
    "constant": ("a", "b", "value"),
    "lean": ("source",),
    "orbit": ("p1", "p2", "tau"),
}

CLAIM_DOC = """Submit a claim to Euresis' claims registry and verification gate. The verifier for its kind
decides the status (proved / verified-numeric / refuted / unverified); the model never does. Same
payload → same claim id. Returns the claim id, status, evidence and novelty verdict.

Payload by kind:
* z3 — {"claim": str, "variables": {"x": "Real"|"Int"|"Bool"}, "assumptions": [str]}: Python/Z3
  syntax (And, Or, Not, Implies, If, sqrt). Proved = Z3 shows the negation unsatisfiable.
* identity — {"lhs": str, "rhs": str, "symbols": [str], "positive": bool}: SymPy syntax. Proved =
  lhs − rhs simplifies to 0 (after 50-digit spot checks); numeric agreement only → verified-numeric.
* inequality — {"P": str, "Q": str, "k": "p/q"} in a, b, c: claims P − P(1,1,1) ≥ k·(Q − Q(1,1,1))
  for all a, b, c > 0. Z3 proof plus 200 000-point sampling; also tests whether k is sharp.
* physics-relation — {"claim": sympy relational str, "symbols": [str]}: all symbols positive,
  square roots allowed. Z3 with exact square roots.
* constant — {"a": expr in n, "b": expr in n, "value": str, "digits": int, "depth": int}: the
  continued fraction a(0) + b(1)/(a(1) + b(2)/(…)) equals value (pi, e, catalan, zeta(3), log(2),
  euler, phi, sqrt). Best possible status: verified-numeric (never proved).
* lean — {"source": str}: a complete Lean 4 file; proved if it type-checks with no sorry.
* orbit — {"p1", "p2", "tau"}: symmetric three-body orbit, interval-arithmetic proof (slow; queued)."""

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
    {"name": "propose", "description": "Record your hypotheses and research plan before testing them. "
     "Hypotheses are stored in the Thought Space as hypotheses — they are never counted as results.",
     "input_schema": _schema({
         "hypotheses": {"type": "array", "items": _schema({"statement": {"type": "string"},
                                                           "rationale": {"type": "string"},
                                                           "test": {"type": "string"}}, ["statement", "test"])},
         "plan": {"type": "array", "items": {"type": "string"}}}, ["hypotheses", "plan"])},
    {"name": "submit_claim", "description": CLAIM_DOC,
     "input_schema": _schema({
         "kind": {"type": "string", "enum": list(CLAIM_FIELDS)},
         "statement": {"type": "string", "description": "the claim in words and standard notation"},
         "payload": {"type": "object", "description": "machine-checkable form; fields depend on kind"},
         "known_as": {"type": "string", "description": "if this is an established result, its name/source"},
         "novelty_keywords": {"type": "array", "items": {"type": "string"}}},
        ["kind", "statement", "payload"])},
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


CLAIM_ID = re.compile(r"\b(?:ine|z3|ide|con|orb|lea|phy)-[0-9a-f]{12}\b")
REPORT_DIR = ROOT / "space" / "research"


def _novelty_from_literature(nov: dict) -> str:
    """Map a literature verdict to the registry's novelty field (``known…`` blocks a discovery)."""
    v = nov["verdict"]
    if v.startswith("likely already published") and nov.get("closest"):
        c = nov["closest"][0]
        return f"known (literature: \"{c.get('title', '')[:120]}\" {c.get('year') or ''}, similarity {c['similarity']})"
    return v


def _payload_hint(kind: str, payload: dict, evidence) -> str:
    """When a verifier could not even read a claim, say how to restate it (the verdict itself is unchanged)."""
    if not (isinstance(evidence, dict) and "error" in evidence):
        return ""
    tips = ["the verifier could not parse this payload — fix it and resubmit (the gate, not you, decides the status)"]
    text = " ".join(json.dumps(v) for v in (payload or {}).values())      # values only, not field names
    if re.search(r"\bgamma\b", text):
        tips.append("'gamma' is SymPy's gamma function: write the Lorentz factor explicitly, 1/sqrt(1 - v**2/c**2)")
    if re.search(r"\b(lambda|beta|E|I|S|N|O|Q)\b", text):
        tips.append("avoid single-letter names that SymPy reserves (E, I, S, N, O, Q) and 'lambda'")
    if kind == "inequality" and not {"a", "b"} <= set(re.findall(r"[A-Za-z_]\w*", text)):
        tips.append("kind 'inequality' is only for symmetric expressions in a, b, c > 0; for a physical relation "
                    "use kind 'physics-relation' with {'claim': 'lhs >= rhs', 'symbols': [...]}")
    tips.append("every symbol must be listed and the payload must use the exact field names for its kind")
    return "; ".join(tips)


LOCAL_SYSTEM = """You are the reasoning core of Euresis, a scientific discovery system. You propose hypotheses and
claims; Euresis' verifiers decide what is true — you never set a claim's status.
1. Search knowledge and literature first. 2. Optionally call propose with hypotheses and a short plan.
3. Explore with computer_algebra, check_dimensions, simulate, run_experiment, run_python (working notes only).
4. Send every claim you will report through submit_claim, stated exactly; say known_as if it is an established result.
5. Final report: cite each result by its claim id in square brackets, e.g. [z3-0123456789ab]; Euresis fills in the
status the gate recorded. Label anything without a claim id as speculation. A discovery is proved AND not known."""


def _compact(tool: dict) -> dict:
    """Shorter tool description for the local model (fewer prompt tokens to read on a CPU). submit_claim keeps its
    payload formats, which the model needs to state claims exactly."""
    d = tool["description"]
    if tool["name"] != "submit_claim":
        d = d.split(". ")[0].rstrip(".") + "."
    else:
        d = ("Submit a claim to the verification gate (it, not you, decides the status). Payloads — z3: {claim, "
             "variables:{x:Real}}; identity: {lhs, rhs, symbols}; inequality: {P, Q, k} in a,b,c>0; physics-relation: "
             "{claim, symbols, assumptions}; constant: {a, b, value} continued fraction.")
    def strip(schema):
        if isinstance(schema, dict):
            return {k: strip(v) for k, v in schema.items() if k != "description"}
        return schema
    return {**tool, "description": d, "input_schema": strip(tool["input_schema"])}


class ReasoningCore:
    def __init__(self, kb: KnowledgeBase, engine: Engine, model, space: ThoughtSpace | None,
                 registry: Registry | None = None, log=print):
        self.kb, self.E, self.model, self.space, self.log = kb, engine, model, space, log
        self.registry = registry or Registry()
        self.retriever = TextRetriever(kb.documents())
        self.ideas = IdeaEngine(kb, engine, model, space, log=lambda *a: None)
        self.qid = None
        self.question = ""
        self.session_claims: list[str] = []      # claim ids submitted in this research session
        self.hypotheses: list[dict] = []
        self.plan: list[str] = []

    # -------------------------------------------------------------- gate
    def submit_claim(self, kind: str, statement: str, payload: dict, known_as: str = "",
                     novelty_keywords: list[str] | None = None) -> dict:
        """Registry → gate → (if proved) novelty. The verifier alone sets the status."""
        if kind not in CLAIM_FIELDS:
            return {"error": f"unknown kind {kind!r}; use one of {list(CLAIM_FIELDS)}", "registered": False}
        missing = [f for f in CLAIM_FIELDS[kind] if f not in (payload or {})]
        if missing:
            return {"error": f"payload for {kind} is missing {missing}", "registered": False}
        src = f"reasoning-core ({getattr(self, 'backend_name', 'Claude')}): {self.question[:80]}"
        cid = self.registry.add(kind, statement, payload, source=src)
        if cid not in self.session_claims:
            self.session_claims.append(cid)
        c = self.registry.get(cid)
        note = ""
        if c["status"] in ("candidate", "unverified"):
            if kind in gate.SLOW_KINDS:
                self.registry.submit("gate", {"claim": cid})
                note = "slow verifier: queued (`python -m euresis jobs work`); status stays candidate until it runs"
            else:
                gate.check(self.registry, cid, log=self.log)
        else:
            note = "already in the registry; existing verdict reused"
        c = self.registry.get(cid)
        if c["status"] == "proved" and not c["novelty"].startswith("known"):
            if known_as:
                self.registry.set_novelty(cid, f"known ({known_as})")
            elif c["novelty"] == "not checked":
                try:
                    nov = literature.novelty(statement, novelty_keywords)
                    self.registry.set_novelty(cid, _novelty_from_literature(nov))
                except Exception as e:           # an unreachable literature search leaves novelty unchecked
                    self.registry.set_novelty(cid, f"unchecked — literature search failed ({type(e).__name__})")
        elif known_as and not c["novelty"].startswith("known"):
            self.registry.set_novelty(cid, f"known ({known_as})")
        c = self.registry.get(cid)
        ev = json.dumps(c.get("evidence"), default=str)
        hint = _payload_hint(kind, payload, c.get("evidence"))
        return {"claim_id": cid, "status": c["status"], "verifier": c.get("verifier"), "label": gate.label(c),
                "novelty": c["novelty"], "is_discovery": gate.is_discovery(c),
                "evidence": ev[:3000], **({"note": note} if note else {}), **({"fix_hint": hint} if hint else {})}

    def claim_table(self) -> list[dict]:
        return [c for c in (self.registry.get(cid) for cid in self.session_claims) if c]

    def final_report(self, text: str) -> str:
        """Rewrite every cited claim id with its gated status and append the authoritative table."""
        def tag(m):
            c = self.registry.get(m.group(0))
            if c is None:
                return f"{m.group(0)} ⟨NOT IN REGISTRY — unverified⟩"
            return f"{m.group(0)} ⟨{gate.label(c)}⟩"
        body = CLAIM_ID.sub(tag, text)
        rows = self.claim_table()
        cited = set(CLAIM_ID.findall(text))
        out = [body.rstrip(), "", "---", "## Verification gate — authoritative claim table",
               "Statuses below were set by Euresis' verifiers (gate.py), not by the language model.", ""]
        if rows:
            out += ["| claim | kind | status | verifier | novelty | statement |", "|---|---|---|---|---|---|"]
            for c in rows:
                st = c["statement"].replace("|", "\\|").replace("\n", " ")
                nov = c["novelty"].replace("|", "\\|")
                out.append(f"| `{c['id']}` | {c['kind']} | **{c['status']}** | {c.get('verifier') or '—'} "
                           f"| {nov} | {st} |")
        else:
            out.append("No claims were submitted to the gate: nothing in this report is a verified result.")
        disc = [c for c in rows if gate.is_discovery(c)]
        counts = {}
        for c in rows:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
        out += ["", "**Totals:** " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"),
                f"**Discoveries (proved AND not known):** {len(disc)}"
                + "".join(f"\n- `{c['id']}` — {c['statement']} (novelty: {c['novelty']})" for c in disc)]
        uncited = [c["id"] for c in rows if c["id"] not in cited]
        if uncited:
            out.append("\nSubmitted but not cited in the narrative: " + ", ".join(f"`{u}`" for u in uncited))
        if self.hypotheses:
            out += ["", "### Hypotheses proposed (not results)"]
            out += [f"- {h['statement']} — test: {h.get('test', '')}" for h in self.hypotheses]
        return "\n".join(out) + "\n"

    def save_report(self, report: str) -> Path:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", self.question.lower()).strip("-")[:60] or "question"
        path = REPORT_DIR / f"{time.strftime('%Y-%m-%d')}-{slug}.md"
        path.write_text(f"# Research: {self.question}\n\n{report}")
        return path

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
        if name == "propose":
            ids = []
            for h in args.get("hypotheses", []):
                self.hypotheses.append(h)
                if self.space is not None:
                    ids.append(self.space.add("hypothesis", h["statement"][:120],
                                              body=f"{h.get('rationale', '')}\nTest: {h.get('test', '')}",
                                              domain="method", parents=[self.qid] if self.qid else [],
                                              status="hypothesis · not a claim", score=0.5))
            self.plan = list(args.get("plan", []))
            return {"recorded_hypotheses": len(args.get("hypotheses", [])), "thought_ids": ids,
                    "note": "hypotheses are not results; submit each testable claim with submit_claim"}
        if name == "submit_claim":
            return self.submit_claim(args["kind"], args["statement"], args.get("payload") or {},
                                     args.get("known_as", ""), args.get("novelty_keywords"))
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
        if self.space is None or name in ("record_idea", "propose", "submit_claim"):
            return
        status = "ok"
        if isinstance(result, dict):
            status = result.get("status") or ("error" if "error" in result else "ok")
        self.space.add("evidence", f"{name}: {json.dumps(args)[:90]}", body=json.dumps(result, default=str)[:1500],
                       domain="method", parents=[self.qid] if self.qid else [], status=f"tool result · {status}",
                       score=0.3)

    # -------------------------------------------------------------- loop
    def research(self, question: str, max_turns: int = 30, client=None, backend: str = "auto",
                 think: bool = False) -> str | None:
        """backend: 'claude' (API), 'local' (Qwen3 8B/14B on this machine), 'auto' (Claude if credentials, else local)."""
        from . import local_llm
        if backend == "auto":
            backend = ("claude" if client is not None or self._has_credentials()
                       else "local" if local_llm.available() else "claude")
        if backend == "local":
            return self._research_local(question, max_turns=min(max_turns, 16), think=think)
        self.backend_name = "Claude"
        try:
            import anthropic
        except ImportError:
            self.log("The `anthropic` package is not installed: pip install anthropic")
            return None
        self.question = question
        if client is None and self._has_credentials():
            client = anthropic.Anthropic()
        if client is None:
            self.log("No Claude credentials: set ANTHROPIC_API_KEY or run `ant auth login`.")
            return None
        if self.space is not None:
            self.qid = self.space.add("question", question, status="research question", domain="method",
                                      body="Investigated by the reasoning core.", score=1.0)
        messages = [{"role": "user", "content": question}]
        for turn in range(max_turns):
            try:
                resp = client.beta.messages.create(
                    model=MODEL, max_tokens=16000, system=SYSTEM, tools=TOOLS, messages=messages,
                    thinking={"type": "adaptive"}, output_config={"effort": "high"},
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            except anthropic.AuthenticationError:
                self.log("Claude rejected the credentials.")
                return self._partial()
            except anthropic.RateLimitError:
                self.log("Rate limited by the Claude API; try again shortly.")
                return self._partial()
            except anthropic.APIStatusError as e:
                self.log(f"Claude API error {e.status_code}: {e.message}")
                return self._partial()
            except anthropic.APIConnectionError:
                self.log("Cannot reach the Claude API (network policy?).")
                return self._partial()
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "refusal":
                self.log("The model declined this request.")
                return self._partial()
            if resp.stop_reason == "pause_turn":
                continue
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                if resp.stop_reason == "max_tokens":
                    messages.append({"role": "user", "content": "Continue."})
                    continue
                text = self.final_report("".join(b.text for b in resp.content if b.type == "text"))
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
        self.ended = f"stopped after the maximum of {max_turns} turns before the model wrote a report or submitted a claim"
        return self._partial()

    # ------------------------------------------------------- local model loop
    LOCAL_TOOLS = ("search_knowledge", "search_literature", "check_novelty", "computer_algebra", "check_dimensions",
                   "propose", "submit_claim", "simulate", "run_experiment", "run_python", "record_idea")

    def _research_local(self, question: str, max_turns: int = 16, think: bool = False) -> str | None:
        """Same tools, same gate, same report — driven by the local Qwen3 model (8B or 14B) on this machine."""
        from . import local_llm
        if not local_llm.available():
            self.log("Local model not installed: `pip install llama-cpp-python` and `python -m euresis local download`.")
            return None
        name = local_llm.MODELS[local_llm.size()]["file"].split("-Q")[0]
        self.backend_name, self.question = f"local {name}", question
        if self.space is not None:
            self.qid = self.space.add("question", question, status="research question", domain="method",
                                      body=f"Investigated by the reasoning core ({self.backend_name}).", score=1.0)
        tools = [_compact(t) for t in TOOLS if t["name"] in self.LOCAL_TOOLS]
        system = LOCAL_SYSTEM + ("\n\nCall tools with <tool_call> blocks as described below. If submit_claim returns a "
                           "fix_hint, correct the payload and resubmit (up to two retries) before reporting. "
                           "When you are finished, write the final report with no tool calls.")
        llm = local_llm.load(log=self.log)
        messages = [{"role": "user", "content": question}]
        for turn in range(max_turns):
            # stay inside the context window: shorten the oldest tool results first
            while len(llm.tokenize(local_llm.render(system, messages, tools, think).encode())) > llm.n_ctx() - 1800:
                old = next((m for m in messages if m["role"] == "tool" and not m.get("short")), None)
                if old is None:
                    break
                old["content"], old["short"] = old["content"][:300] + " …[shortened]", True
            r = local_llm.complete(system, messages, tools, think=think, max_tokens=1500, log=self.log)
            self.log(f"  [{turn + 1}] local model: {r['prompt_tokens']} prompt + {r['completion_tokens']} new tokens "
                     f"in {r['seconds']} s")
            messages.append({"role": "assistant", "content": re.sub(r"<think>.*?</think>", "", r["raw"], flags=re.S).strip()})
            if not r["calls"]:
                text = self.final_report(r["text"])
                if self.space is not None:
                    self.space.add("insight", f"Research report: {question[:80]}", body=text[:6000], domain="method",
                                   parents=[self.qid], status=f"reasoning-core report ({self.backend_name})", score=1.0)
                return text
            for c in r["calls"]:
                self.log(f"      {c['name']}({json.dumps(c['arguments'])[:110]})")
                try:
                    out = (self.execute(c["name"], c["arguments"]) if c["name"] in self.LOCAL_TOOLS
                           else {"error": f"unknown or unavailable tool {c['name']}"})
                except Exception as e:     # tool failure is reported to the model, not hidden
                    out = {"error": f"{type(e).__name__}: {e}"}
                self._note(c["name"], c["arguments"], out)
                messages.append({"role": "tool", "content": json.dumps(out, default=str)[:2500]})
        self.log("Stopped after the maximum number of turns.")
        self.ended = f"stopped after the maximum of {max_turns} turns before the model wrote a report or submitted a claim"
        return self._partial()

    def _partial(self) -> str | None:
        """The run ended early: report what the gate decided so far (nothing if no claims)."""
        if not self.session_claims:
            return None
        return self.final_report("*The run ended before the model wrote its report; only gated claims are shown.*")

    @staticmethod
    def _has_credentials() -> bool:
        import os
        from pathlib import Path
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                    or (Path.home() / ".config" / "anthropic").exists())
