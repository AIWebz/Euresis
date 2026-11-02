"""Rediscovery benchmark — can Euresis find laws it was never told?

A set of well-known laws is removed from the knowledge base *and* from the
model's training data. Euresis then explores from the remaining knowledge, and
we check whether any of its outputs is the removed law (exactly, or up to a
dimensionless constant, which dimensional analysis cannot fix).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .engine import Engine
from .explorer import Explorer
from .kb import KnowledgeBase
from .model import ConceptEmbedding, train

HOLDOUT = [
    "Gravitational potential energy",
    "Surface gravity",
    "Circular orbital velocity",
    "Escape velocity",
    "Simple pendulum period",
    "Schwarzschild radius",
    "Kepler's third law",
    "Stokes' law",
    "Compton wavelength",
    "Potential of a point charge",
]


def run(cycles: int = 2, out: Path | None = None, log=print) -> dict:
    t0 = time.time()
    kb = KnowledgeBase(exclude=set(HOLDOUT))
    mdir = Path(__file__).resolve().parent.parent / "models" / "benchmark"
    train(kb, out_dir=mdir, verbose=False)
    model = ConceptEmbedding.load(mdir / "euresis-concepts.npz")
    eng = Engine(kb, model)
    ex = Explorer(kb, eng, model, space=None, log=lambda *a: log("   ", *a))
    ex.run(cycles=cycles)
    rels = [r for r in ex.results if "relation" in r]
    report = {"held_out": len(kb.held_out), "results_examined": len(rels), "laws": []}
    for f in kb.held_out:
        hit = None
        for r in rels:
            try:
                ratio = eng.equivalent(r["relation"], f)
            except Exception:
                ratio = None
            if ratio is not None:
                exact = ratio in (1, -1)
                cand = {"law": f.name, "found": True, "exact": bool(exact), "factor": str(ratio),
                        "method": r["method"], "as": r["pretty"]}
                if hit is None or (exact and not hit["exact"]):
                    hit = cand
                if exact:
                    break
        report["laws"].append(hit or {"law": f.name, "found": False})
    found = sum(1 for l in report["laws"] if l["found"])
    exact = sum(1 for l in report["laws"] if l.get("exact"))
    report.update(found=found, exact=exact, recall=found / len(kb.held_out), seconds=round(time.time() - t0, 1))
    log(f"Rediscovery benchmark: {found}/{len(kb.held_out)} held-out laws rediscovered "
        f"({exact} exactly, {found - exact} up to a dimensionless constant) in {report['seconds']} s")
    for l in report["laws"]:
        mark = "✔" if l["found"] else "✘"
        extra = f"via {l['method']}: {l['as']}" + ("" if l.get("exact") else f"  [factor {l['factor']}]") if l["found"] else ""
        log(f"  {mark} {l['law']:34s} {extra}")
    if out:
        Path(out).write_text(json.dumps(report, indent=2))
    return report
