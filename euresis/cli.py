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
    from .discover import DataDiscoverer, builtin, load_csv
    from .render import export
    from .space import ThoughtSpace
    kb, eng, _ = _load(with_model=False)
    space = ThoughtSpace()
    dd = DataDiscoverer(kb, eng, space)
    if a.csv:
        mapping = dict(m.split(":") for m in a.map)
        sets = [load_csv(a.csv, a.target, mapping)]
    else:
        sets = [d for d in builtin() if not a.dataset or d.name == a.dataset]
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
    answer = llm.ask(q, context) if llm.available() else None
    if answer:
        print("\nEuresis (via Claude):\n" + answer)
    else:
        print("\n(Offline mode — install `anthropic` and set credentials for written explanations.)")
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


def main(argv=None):
    p = argparse.ArgumentParser(prog="euresis", description="Euresis — scientific discovery engine")
    sub = p.add_subparsers(dest="cmd", required=True)
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
    b = sub.add_parser("benchmark"); b.add_argument("--cycles", type=int, default=3); b.set_defaults(fn=cmd_benchmark)
    s = sub.add_parser("solve"); s.add_argument("formula"); s.add_argument("target", nargs="?", default="")
    s.add_argument("values", nargs="*"); s.set_defaults(fn=cmd_solve)
    k = sub.add_parser("ask"); k.add_argument("question"); k.set_defaults(fn=cmd_ask)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
