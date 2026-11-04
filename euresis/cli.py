"""Command-line interface:  python -m euresis <command>"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(with_model=True):
    from .engine import Engine
    from .kb import KnowledgeBase
    from .model import load_or_train
    kb = KnowledgeBase()
    model = load_or_train(kb) if with_model else None
    return kb, Engine(kb, model), model


def cmd_info(a):
    from .kb import KnowledgeBase
    kb = KnowledgeBase()
    s = kb.stats()
    print("Euresis knowledge base")
    for k, v in s.items():
        print(f"  {k:12s} {v}")
    print("  fields       " + ", ".join(kb.domains))


def cmd_train(a):
    from .kb import KnowledgeBase
    from .model import train
    train(KnowledgeBase(), epochs=a.epochs)


def cmd_explore(a):
    from .explorer import Explorer
    from .render import export
    from .space import SPACE_DIR, ThoughtSpace
    kb, eng, model = _load()
    path = SPACE_DIR / "thoughts.jsonl"
    if a.fresh and path.exists():
        path.unlink()
    space = ThoughtSpace(path)
    start = 1 + max((t["cycle"] for t in space.thoughts.values()), default=0)
    ex = Explorer(kb, eng, model, space, seed=a.seed)
    ex.run(cycles=a.cycles, start=start)   # re-seeding is idempotent: existing thoughts are reused
    rows = ex.report(SPACE_DIR / "discoveries.md")
    print("thought space:", space.stats())
    print(f"{len(ex.candidates)} candidate discoveries; top {len(rows)} written to space/discoveries.md")
    out = export()
    print(f"canvas written to {out.relative_to(ROOT)}")


def cmd_discover(a):
    """Find laws in measured data (built-in real datasets, or your CSV)."""
    import warnings
    warnings.filterwarnings("ignore")
    from .discover import DataDiscoverer, builtin, load_csv, simulated
    from .render import export
    from .space import ThoughtSpace
    kb, eng, _ = _load(with_model=False)
    space = ThoughtSpace()
    dd = DataDiscoverer(kb, eng, space)
    if a.csv:
        mapping = dict(m.split(":") for m in a.map)
        sets = [load_csv(a.csv, a.target, mapping)]
    else:
        sets = [d for d in builtin() + simulated() if not a.dataset or d.name == a.dataset]
    for ds in sets:
        dd.run(ds)
        print()
    export()


def cmd_connect(a):
    """Ask Claude for new ideas at Euresis' connection points; Euresis verifies each one."""
    from .connect import IdeaEngine
    from .render import export
    from .space import ThoughtSpace
    kb, eng, model = _load()
    ie = IdeaEngine(kb, eng, model, ThoughtSpace(), seed=a.seed)
    summary = ie.run(n_points=a.points, ideas_per_point=a.ideas)
    print(summary)
    if not summary["online"]:
        print("Claude was not reachable: set ANTHROPIC_API_KEY (or run `ant auth login`) and `pip install anthropic`.")
    export()


def cmd_research(a):
    """Claude as reasoning core, with Euresis' verified tools."""
    from .agent import ReasoningCore
    from .render import export
    from .space import ThoughtSpace
    kb, eng, model = _load()
    core = ReasoningCore(kb, eng, model, ThoughtSpace())
    report = core.research(a.question, max_turns=a.max_turns, backend=a.backend, think=a.think)
    if report:
        print("\n" + report)
        print(f"report saved to {core.save_report(report).relative_to(ROOT)}; claims in space/claims.json")
    else:
        print("No report: no language model was reachable (see message above). Nothing was claimed.")
    export()


def cmd_claude_ping(a):
    """Confirm Claude credentials with one minimal API call (the key itself is never printed)."""
    from .llm import ping
    r = ping()
    for k, v in r.items():
        print(f"  {k:14s} {v}")
    sys.exit(0 if r["ok"] else 1)


def cmd_literature(a):
    from . import literature
    if a.action == "search":
        papers, status = literature.search(" ".join(a.query), a.n, log=print)
        for p in papers[: a.n]:
            print(f"- {p.title} ({p.year}, {p.source}) {p.url}")
    elif a.action == "harvest":
        literature.harvest([" ".join(a.query)], per_query=a.n)
    elif a.action == "novelty":
        r = literature.novelty(" ".join(a.query), log=print)
        print(r["verdict"])
        for c in r["closest"]:
            print(f"  {c['similarity']:.2f}  {c['title']} ({c['year']}) {c['url']}")
    print(f"local index: {literature.Library().count()} papers")


def cmd_simulate(a):
    from .simulate import run
    params = {}
    for kv in a.params:
        k, v = kv.split("=", 1)
        try:
            params[k] = json.loads(v)
        except json.JSONDecodeError:
            params[k] = v
    print(json.dumps(run(a.model, **params), indent=2, default=float))


def cmd_prove(a):
    from .verify import check_lean, prove_z3
    if a.lean:
        print(check_lean(Path(a.lean).read_text()))
    else:
        variables = dict(v.split(":") for v in a.vars)
        print(prove_z3(a.claim, variables, a.assume))


def cmd_sandbox(a):
    from .verify import run_python
    r = run_python(Path(a.file).read_text(), timeout=a.timeout)
    print(r["stdout"], end="")
    if r["stderr"]:
        print(r["stderr"], file=sys.stderr, end="")
    print(f"[{r['status']}]")


def cmd_lawbench(a):
    """Law-discovery benchmark over the knowledge base."""
    import warnings
    warnings.filterwarnings("ignore")
    from .srbench import run
    run(noise=a.noise, limit=a.limit or None, processes=a.processes)


def cmd_findlaw(a):
    """Symbolic regression on a CSV: --dims col:'M L T-2' ... --target col."""
    import csv as _csv
    import numpy as np
    from .dimensions import D
    from .sr import regress
    rows = list(_csv.DictReader(open(a.csv)))
    dims = dict(x.split(":", 1) for x in a.dims)
    names = [c for c in dims if c != a.target]
    X = np.array([[float(r[c]) for c in names] for r in rows])
    y = np.array([float(r[a.target]) for r in rows])
    r = regress(X, y, [D(dims[c]) for c in names], D(dims[a.target]), names, noise=a.noise)
    if r is None:
        print("no law found")
        return
    print(f"{a.target} = {r['expr']}")
    print(f"exact: {r['exact']}  relative error: {r['val_err']:.2e}  form: {r['family']}  Π groups: {r['pi_groups']}")


def cmd_mysteries(a):
    """Pose the open mysteries in knowledge/mysteries.txt; Euresis works on each one itself."""
    import warnings
    warnings.filterwarnings("ignore")
    from .mysteries import run
    run(ids=a.ids or None)


def cmd_lm(a):
    """Euresis-LM: train, evaluate, ask (which laws a question is about), explain, generate."""
    import warnings
    warnings.filterwarnings("ignore")
    from .lm.model import Config, EuresisLM
    if a.action == "train":
        from .lm.corpus import build
        docs, _, _ = build()
        EuresisLM.train(docs, Config(layers=a.layers, d=a.d, heads=a.heads), steps=a.steps)
        return
    if a.action == "train-papers":
        from .lm.corpus import build_with_papers
        from .lm.model import MODEL_DIR
        docs, _, _ = build_with_papers()
        EuresisLM.train(docs, Config(vocab=8192, layers=a.layers, d=a.d, heads=a.heads), steps=a.steps,
                        out_dir=MODEL_DIR.parent / "euresis-lm2")
        return
    if a.action == "eval":
        from .lm.evaluate import evaluate
        evaluate()
        return
    from .lm.model import MODEL_DIR
    lm = EuresisLM.load(MODEL_DIR.parent / "euresis-lm2-ft") if a.model == "papers" else EuresisLM.load()
    text = " ".join(a.text)
    if a.action == "ask":
        from .kb import KnowledgeBase
        kb = KnowledgeBase()
        for name, sc in lm.rank(text, [f.name for f in kb.formulas])[:5]:
            f = kb.by_name(name)
            print(f"  {sc:7.3f}  {name}: {f.pretty()}")
    elif a.action == "explain":
        print(lm.generate(f"explain: {text}\nanswer:", max_new=90, temperature=0.4))
    else:
        print(lm.generate(text, max_new=120, temperature=a.temperature))


def cmd_conjecture(a):
    """Search continued fractions for new formulas for fundamental constants."""
    from .conjecture import run
    from .render import export
    from .space import ThoughtSpace
    mode = {"basic": False, "frontier": True, "sweep": "sweep"}[a.mode]
    run(space=ThoughtSpace(), frontier=mode)
    export()


def cmd_findnew(a):
    """Keep searching until a formula passes every available novelty check."""
    from .novelty_math import run
    from .render import export
    from .space import ThoughtSpace
    found, recs = run(max_minutes=a.minutes, space=ThoughtSpace())
    print("FOUND" if found else "not found", found or "")
    export()


def cmd_read_papers(a):
    """Ingest the paper corpus and discover while reading (literature-based discovery)."""
    import warnings
    warnings.filterwarnings("ignore")
    from .papers import run
    from .render import export
    from .space import ThoughtSpace
    run(space=ThoughtSpace())
    export()


def cmd_answer(a):
    """Answer a question from Euresis' measured facts, principles and laws."""
    import warnings
    warnings.filterwarnings("ignore")
    from .answer import Answerer
    print(Answerer().answer(" ".join(a.question))["text"])


def cmd_prove_new(a):
    """Discover sharp inequalities and prove them; runs until a proven, non-classical theorem is found."""
    import warnings
    warnings.filterwarnings("ignore")
    from .render import export
    from .space import ThoughtSpace
    from .theorems import run
    best, found = run(space=ThoughtSpace())
    print("\nRESULT:", best)
    export()


def cmd_prove_physics(a):
    """Discover and prove sharp relations between laws that predict the same quantity."""
    import warnings
    warnings.filterwarnings("ignore")
    from .physics_theorems import run
    from .space import ThoughtSpace
    run(space=ThoughtSpace())


def cmd_learn(a):
    """Feed Euresis new knowledge from a text file, validate it, and retrain."""
    import shutil
    from .kb import USER_DIR, KnowledgeBase
    from .model import train
    USER_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(a.file)
    dst = USER_DIR / src.name
    shutil.copy(src, dst)
    kb = KnowledgeBase()
    if kb.errors:
        print("rejected (not dimensionally consistent or malformed):")
        for e in kb.errors:
            print("  -", e)
    print("knowledge base now:", kb.stats())
    train(kb)


def cmd_render(a):
    from .render import export
    print(export())


def cmd_benchmark(a):
    from .benchmark import run
    from .space import SPACE_DIR
    run(cycles=a.cycles, out=SPACE_DIR / "benchmark.json")


def cmd_solve(a):
    import sympy as sp
    kb, eng, _ = _load(with_model=False)
    f = kb.by_name(a.formula) or next((x for x in kb.formulas if a.formula.lower() in x.name.lower()), None)
    if not f:
        sys.exit(f"no formula matching '{a.formula}'")
    print(f"{f.name}:  {f.pretty()}")
    target = next((s for s, q in f.sym_to_q.items() if q == a.target or f.display.get(s) == sp.Symbol(a.target)), None)
    if target is None:
        print("variables:", ", ".join(f"{f.display[s]} ({q})" for s, q in f.sym_to_q.items()))
        return
    for sol in eng.solve_for(f, target):
        print(f"  {f.display[target]} = {sp.sstr(sol.subs(f.display))}".replace("**", "^"))
    if a.values:
        vals = {}
        for kv in a.values:
            k, v = kv.split("=")
            q = next((q for s, q in f.sym_to_q.items() if q == k or str(f.display[s]) == k), k)
            vals[q] = float(v)
        print(f"  => {f.sym_to_q[target]} = {eng.evaluate(f, f.sym_to_q[target], vals):.6g} (SI)")


def cmd_ask(a):
    from . import llm
    from .model import TextRetriever
    from .space import ThoughtSpace
    kb, eng, _ = _load(with_model=False)
    retr = TextRetriever(kb.documents())
    q = a.question
    expanded = q + " " + " ".join(SYN.get(w.lower(), "") for w in re.findall(r"\w+", q))
    hits = retr.search(expanded, k=6)
    lines = []
    for (kind, title, text), s in hits:
        f = kb.by_name(title)
        lines.append(f"- [{kind}] {title}: {f.pretty() if f else text}")
    space = ThoughtSpace()
    related = [t for t in space.thoughts.values()
               if t["kind"] in ("derivation", "hypothesis", "scale", "prediction", "dimensional")
               and any(w in (t["title"] + t["body"]).lower() for w in re.findall(r"[a-z]{5,}", q.lower()))][:5]
    for t in related:
        lines.append(f"- [euresis {t['kind']}] {t['title']}: {t['formula']} ({t['status']})")
    context = "\n".join(lines)
    print("Relevant knowledge:\n" + context)
    from . import local_llm
    from .agent import ReasoningCore
    answer, via = None, None
    if llm.available() and ReasoningCore._has_credentials():
        answer, via = llm.ask(q, context), "Claude"
    if not answer and local_llm.available():
        answer, via = local_llm.ask(q, context), "local Qwen3-14B"
    if answer:
        print(f"\nEuresis (via {via}):\n" + answer)
    else:
        print("\n(Offline mode — no language model: set ANTHROPIC_API_KEY, or `python -m euresis local download`.)")
    qid = space.add("question", q, body=answer or "answered from knowledge base", status="asked by user",
                    domain="physics", parents=[space.make_id("law", f"law|{h[0][1]}") for h in hits
                                               if space.make_id("law", f"law|{h[0][1]}") in space.thoughts])
    print(f"\nrecorded in the Thought Space as {qid}")


SYN = {"fast": "velocity speed", "speed": "velocity", "leave": "escape", "planet": "gravitation mass radius",
       "orbit": "orbital kepler", "hot": "temperature", "heat": "thermodynamics temperature",
       "light": "photon wavelength speed", "atom": "atomic bohr", "star": "stellar luminosity",
       "black": "schwarzschild", "hole": "schwarzschild", "electricity": "current voltage",
       "battery": "cell potential emf", "acid": "ph", "enzyme": "michaelis", "virus": "reproduction",
       "evolution": "selection", "gene": "allele", "earthquake": "seismic magnitude"}


def cmd_collect(a):
    from . import collect
    collect.run()


def cmd_gate(a):
    from . import gate
    print(gate.run(include_slow=a.slow, recheck=a.recheck))


def cmd_claims(a):
    from . import gate
    from .registry import Registry
    reg = Registry()
    for c in reg.claims(status=a.status or None, kind=a.kind or None):
        print(f"{c['id']}  [{gate.label(c)}]  {c['statement']}")
    print(reg.stats())


def cmd_jobs(a):
    from . import jobs
    from .registry import Registry
    reg = Registry()
    if a.action == "work":
        n = jobs.work(reg, forever=a.forever)
        print(f"{n} job(s) processed")
    else:
        for j in reg.jobs():
            print(f"{j['id']:4d} {j['state']:8s} {j['kind']} {j['args']}" + (f"  error: {j['error'][:80]}" if j["error"] else ""))


def cmd_scorecard(a):
    from . import scorecard
    scorecard.run()


def cmd_writeup(a):
    from . import writeup
    writeup.run()


def cmd_local(a):
    from . import local_llm
    if a.action == "download":
        local_llm.download()
    elif a.action == "info":
        print(json.dumps({**local_llm.MODEL_INFO, "path": str(local_llm.model_path()),
                          "installed": local_llm.available()}, indent=1))
    else:
        if not local_llm.available():
            print("Local model not installed: `pip install llama-cpp-python` and `python -m euresis local download`.")
            return
        r = local_llm.complete("You are Euresis, a careful scientific assistant. Be precise; say when something is "
                               "uncertain.", [{"role": "user", "content": " ".join(a.text)}], think=a.think,
                               max_tokens=1500)
        print(r["text"])
        print(f"[{r['prompt_tokens']} prompt + {r['completion_tokens']} new tokens in {r['seconds']} s]")


def cmd_discover_new(a):
    from . import discover_loop
    if a.stop:
        discover_loop.STOP.parent.mkdir(parents=True, exist_ok=True)
        discover_loop.STOP.write_text("stop requested\n")
        print("stop requested: the discovery loop will stop after its current round")
        return
    discover_loop.STOP.unlink(missing_ok=True) if a.resume else None
    st = discover_loop.run(minutes=a.minutes, use_llm=False if a.no_llm else None)
    print(f"{st['rounds']} rounds, {len(st['discoveries'])} discoveries; log: space/discovery_log.md")


def cmd_physics_discover(a):
    from . import physics_discover
    if a.stop:
        physics_discover.STOP.parent.mkdir(parents=True, exist_ok=True)
        physics_discover.STOP.write_text("stop requested\n")
        print("stop requested: the physics discovery loop will stop after its current round")
        return
    if a.resume:
        physics_discover.STOP.unlink(missing_ok=True)
    st = physics_discover.run(minutes=a.minutes, use_llm=False if a.no_llm else None)
    print(f"{st['rounds']} rounds, {len(st['discoveries'])} discoveries, {len(st['rediscoveries'])} known laws "
          "rediscovered; log: space/physics_discovery_log.md")


def cmd_physics_discover2(a):
    from . import physics_discover2 as pd2
    if a.stop:
        pd2.STOP.parent.mkdir(parents=True, exist_ok=True)
        pd2.STOP.write_text("stop requested\n")
        print("stop requested: the two-variable discovery loop will stop after its current round")
        return
    if a.resume:
        pd2.STOP.unlink(missing_ok=True)
    st = pd2.run(minutes=a.minutes, use_llm=False if a.no_llm else None)
    print(f"{st['rounds']} rounds, {len(st['discoveries'])} discoveries, {len(st['rediscoveries'])} known laws "
          "rediscovered; log: space/physics2_log.md")


def cmd_subjects(a):
    from . import subjects
    subjects.run(max_game_digits=a.game_digits, game_minutes=a.game_minutes)


def main(argv=None):
    p = argparse.ArgumentParser(prog="euresis", description="Euresis — scientific discovery engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect", help="import engine results into the claims registry").set_defaults(fn=cmd_collect)
    g = sub.add_parser("gate", help="verify every unchecked claim"); g.add_argument("--slow", action="store_true",
                       help="run slow verifiers (orbit proofs) inline instead of queueing them")
    g.add_argument("--recheck", action="store_true"); g.set_defaults(fn=cmd_gate)
    cl = sub.add_parser("claims"); cl.add_argument("--status", default=""); cl.add_argument("--kind", default="")
    cl.set_defaults(fn=cmd_claims)
    jb = sub.add_parser("jobs"); jb.add_argument("action", choices=["list", "work"], nargs="?", default="list")
    jb.add_argument("--forever", action="store_true"); jb.set_defaults(fn=cmd_jobs)
    sub.add_parser("scorecard").set_defaults(fn=cmd_scorecard)
    dn = sub.add_parser("discover-new", help="open-ended proved-discovery loop (runs until stopped)")
    dn.add_argument("--minutes", type=float, default=100); dn.add_argument("--no-llm", action="store_true")
    dn.add_argument("--stop", action="store_true", help="ask a running loop to stop")
    dn.add_argument("--resume", action="store_true", help="clear a previous stop request first")
    dn.set_defaults(fn=cmd_discover_new)
    pd = sub.add_parser("physics-discover", help="proved physics discoveries: sharp bounds between physical quantities")
    pd.add_argument("--minutes", type=float, default=100); pd.add_argument("--no-llm", action="store_true")
    pd.add_argument("--stop", action="store_true"); pd.add_argument("--resume", action="store_true")
    pd.set_defaults(fn=cmd_physics_discover)
    p2 = sub.add_parser("physics-discover2", help="two-variable physics discovery (sharp proved bounds over 2-D domains)")
    p2.add_argument("--minutes", type=float, default=100); p2.add_argument("--no-llm", action="store_true")
    p2.add_argument("--stop", action="store_true"); p2.add_argument("--resume", action="store_true")
    p2.set_defaults(fn=cmd_physics_discover2)
    sj = sub.add_parser("discover-subjects", help="music theory, linguistics, game theory (economics: physics-discover2)")
    sj.add_argument("--game-digits", type=int, default=3); sj.add_argument("--game-minutes", type=float, default=30)
    sj.set_defaults(fn=cmd_subjects)
    sub.add_parser("claude-ping", help="one test call to the Claude API").set_defaults(fn=cmd_claude_ping)
    sub.add_parser("writeup").set_defaults(fn=cmd_writeup)
    sub.add_parser("info").set_defaults(fn=cmd_info)
    t = sub.add_parser("train"); t.add_argument("--epochs", type=int, default=400); t.set_defaults(fn=cmd_train)
    e = sub.add_parser("explore"); e.add_argument("--cycles", type=int, default=3)
    e.add_argument("--fresh", action="store_true"); e.add_argument("--seed", type=int, default=1)
    e.set_defaults(fn=cmd_explore)
    sub.add_parser("render").set_defaults(fn=cmd_render)
    l = sub.add_parser("learn"); l.add_argument("file"); l.set_defaults(fn=cmd_learn)
    d = sub.add_parser("discover"); d.add_argument("--dataset", default="")
    d.add_argument("--csv", default=""); d.add_argument("--target", default="")
    d.add_argument("--map", nargs="*", default=[], help="column:quantity_id pairs")
    d.set_defaults(fn=cmd_discover)
    c = sub.add_parser("connect"); c.add_argument("--points", type=int, default=6)
    c.add_argument("--ideas", type=int, default=3); c.add_argument("--seed", type=int, default=0)
    c.set_defaults(fn=cmd_connect)
    r = sub.add_parser("research"); r.add_argument("question"); r.add_argument("--max-turns", type=int, default=30)
    r.add_argument("--backend", choices=["auto", "claude", "local"], default="auto",
                   help="claude = API; local = Qwen3-14B on this machine; auto = Claude if credentials, else local")
    r.add_argument("--think", action="store_true", help="local model: enable step-by-step thinking (much slower)")
    r.set_defaults(fn=cmd_research)
    lo = sub.add_parser("local", help="the local 14B language model")
    lo.add_argument("action", choices=["download", "info", "chat"]); lo.add_argument("text", nargs="*")
    lo.add_argument("--think", action="store_true"); lo.set_defaults(fn=cmd_local)
    li = sub.add_parser("literature"); li.add_argument("action", choices=["search", "harvest", "novelty"])
    li.add_argument("query", nargs="+"); li.add_argument("-n", type=int, default=10); li.set_defaults(fn=cmd_literature)
    si = sub.add_parser("simulate"); si.add_argument("model"); si.add_argument("params", nargs="*")
    si.set_defaults(fn=cmd_simulate)
    pr = sub.add_parser("prove"); pr.add_argument("claim", nargs="?", default="")
    pr.add_argument("--vars", nargs="*", default=[], help="name:Real|Int|Bool")
    pr.add_argument("--assume", nargs="*", default=[]); pr.add_argument("--lean", default="")
    pr.set_defaults(fn=cmd_prove)
    sb = sub.add_parser("sandbox"); sb.add_argument("file"); sb.add_argument("--timeout", type=int, default=60)
    sb.set_defaults(fn=cmd_sandbox)
    lmp = sub.add_parser("lm"); lmp.add_argument("action", choices=["train", "train-papers", "eval", "ask", "explain", "generate"])
    lmp.add_argument("text", nargs="*"); lmp.add_argument("--steps", type=int, default=2500)
    lmp.add_argument("--layers", type=int, default=6); lmp.add_argument("--d", type=int, default=256)
    lmp.add_argument("--heads", type=int, default=8); lmp.add_argument("--temperature", type=float, default=0.7)
    lmp.add_argument("--model", choices=["science", "papers"], default="science",
                     help="science = Euresis-LM 1 (question understanding); papers = Euresis-LM 2 (medical literature)")
    lmp.set_defaults(fn=cmd_lm)
    cj = sub.add_parser("conjecture"); cj.add_argument("mode", nargs="?", default="sweep",
                                                       choices=["basic", "frontier", "sweep"])
    cj.set_defaults(fn=cmd_conjecture)
    fn = sub.add_parser("find-new"); fn.add_argument("--minutes", type=float, default=120)
    fn.set_defaults(fn=cmd_findnew)
    sub.add_parser("read-papers").set_defaults(fn=cmd_read_papers)
    an = sub.add_parser("answer"); an.add_argument("question", nargs="+"); an.set_defaults(fn=cmd_answer)
    sub.add_parser("prove-new").set_defaults(fn=cmd_prove_new)
    sub.add_parser("prove-physics").set_defaults(fn=cmd_prove_physics)
    my = sub.add_parser("mysteries"); my.add_argument("ids", nargs="*"); my.set_defaults(fn=cmd_mysteries)
    lb = sub.add_parser("lawbench"); lb.add_argument("--noise", type=float, default=0.0)
    lb.add_argument("--limit", type=int, default=0); lb.add_argument("--processes", type=int, default=4)
    lb.set_defaults(fn=cmd_lawbench)
    fl = sub.add_parser("findlaw"); fl.add_argument("csv"); fl.add_argument("--target", required=True)
    fl.add_argument("--dims", nargs="+", required=True, help="column:'SI dimension', e.g. v:'L T-1' m:M")
    fl.add_argument("--noise", type=float, default=0.0, help="expected relative measurement error")
    fl.set_defaults(fn=cmd_findlaw)
    b = sub.add_parser("benchmark"); b.add_argument("--cycles", type=int, default=3); b.set_defaults(fn=cmd_benchmark)
    s = sub.add_parser("solve"); s.add_argument("formula"); s.add_argument("target", nargs="?", default="")
    s.add_argument("values", nargs="*"); s.set_defaults(fn=cmd_solve)
    k = sub.add_parser("ask"); k.add_argument("question"); k.set_defaults(fn=cmd_ask)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
