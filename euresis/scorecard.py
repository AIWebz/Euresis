"""Euresis scorecard — one page that says how good Euresis measurably is.

1. **Gate self-test** (run live): claims whose truth is known in advance are fed
   through the verification gate; it must prove the true ones and refute the
   false ones. A gate that accepts a false claim is broken.
2. **Benchmarks** (read from their latest result files): rediscovery of held-out
   laws, symbolic regression on 345 laws (clean / 1 % noise), literature-based
   discovery tested on papers published later.
3. **Claims**: every claim in the registry with its honest status.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import gate
from .registry import ROOT, Registry

SPACE = ROOT / "space"

# (kind, payload, expected status, description)
SELF_TEST = [
    ("inequality", {"P": "(a+b+c)**3/(27*a*b*c)", "Q": "1", "k": "1", "check_sharp": False},
     "proved", "AM–GM: (a+b+c)³ ≥ 27abc (true)"),
    ("inequality", {"P": "(a+b+c)**3/(27*a*b*c)", "Q": "(a**2+b**2+c**2)/(a*b+b*c+c*a)", "k": "1", "check_sharp": False},
     "refuted", "(a+b+c)³/27abc − 1 ≥ (a²+b²+c²)/(ab+bc+ca) − 1 (false at a=b=1, c=2)"),
    ("inequality", {"P": "a/(b+c)+b/(c+a)+c/(a+b)", "Q": "3*(a**2+b**2+c**2)/(a+b+c)**2", "k": "2", "check_sharp": False},
     "refuted", "Nesbitt bound with constant 2 (false: sharp constant is 1)"),
    ("z3", {"claim": "x**2 + y**2 >= 2*x*y", "variables": {"x": "Real", "y": "Real"}}, "proved", "x² + y² ≥ 2xy"),
    ("z3", {"claim": "x**2 >= x", "variables": {"x": "Real"}}, "refuted", "x² ≥ x for all real x (false at x = 1/2)"),
    ("identity", {"lhs": "sin(x)**2 + cos(x)**2", "rhs": "1", "symbols": ["x"]}, "proved", "sin² + cos² = 1"),
    ("identity", {"lhs": "(x + y)**2", "rhs": "x**2 + y**2", "symbols": ["x", "y"]}, "refuted", "(x+y)² = x² + y² (false)"),
    ("constant", {"a": "2*n + 1", "b": "n**2", "value": "4/pi", "digits": 60, "depth": 800},
     "verified-numeric", "4/π = 1 + 1/(3 + 4/(5 + 9/(7 + …))) (true)"),
    ("constant", {"a": "2*n + 1", "b": "n**2", "value": "4/pi + mpf(10)**-40", "digits": 60, "depth": 800},
     "refuted", "the same fraction equals 4/π + 10⁻⁴⁰ (false at digit 40)"),
    ("constant", {"a": "2", "b": "1", "value": "1 + sqrt(2)", "digits": 80, "depth": 400},
     "verified-numeric", "2 + 1/(2 + 1/(2 + …)) = 1 + √2 (true)"),
    ("physics-relation", {"claim": "m*c**2/sqrt(1 - v**2/c**2) >= m*c**2*(1/sqrt(1 - v**2/c**2) - 1)",
                          "symbols": ["c", "m", "v"]}, "proved", "relativistic K ≤ E (true)"),
    ("physics-relation", {"claim": "m*v**2/2 >= m*c**2*(1/sqrt(1 - v**2/c**2) - 1)", "symbols": ["c", "m", "v"]},
     "refuted", "classical KE ≥ relativistic KE (false)"),
    ("physics-relation", {"claim": "m*c**2/sqrt(1 - v**2/c**2) - m*c**2 >= m*v**2/2", "symbols": ["c", "m", "v"]},
     "proved", "relativistic KE ≥ ½mv² (true; regression: no fake counterexample at v = c)"),
    ("physics-relation", {"claim": "m*c**2/sqrt(1 - v**2/c**2) - m*c**2 <= m*v**2/2", "symbols": ["c", "m", "v"]},
     "refuted", "relativistic KE ≤ ½mv² (false; regression: '≤' must not be checked as '≥')"),
]


def self_test(log=print) -> dict:
    rows, ok = [], 0
    for kind, payload, expected, desc in SELF_TEST:
        _, fn = gate.VERIFIERS[kind]
        t0 = time.time()
        try:
            status, _ = fn(payload)
        except Exception as e:
            status = f"error: {e}"
        good = status == expected
        ok += good
        rows.append({"claim": desc, "kind": kind, "expected": expected, "got": status, "pass": good,
                     "seconds": round(time.time() - t0, 2)})
        log(f"  {'PASS' if good else 'FAIL'}  {desc}: expected {expected}, got {status}")
    return {"passed": ok, "total": len(rows), "rows": rows}


def _read(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text()), time.strftime("%Y-%m-%d", time.gmtime(path.stat().st_mtime))


def benchmarks() -> list[dict]:
    out = []
    r = _read(SPACE / "benchmark.json")
    if r:
        d, date = r
        out.append({"name": "Rediscovery of held-out laws", "result": f"{round(d['recall'] * d['held_out'])}/{d['held_out']} recovered "
                    f"({d['exact']} exactly)", "date": date, "source": "space/benchmark.json"})
    for f, label in (("srbench_clean.json", "no noise"), ("srbench_noise10.json", "1% noise")):
        r = _read(SPACE / f)
        if r:
            s, date = r[0]["summary"], r[1]
            out.append({"name": f"Symbolic regression, 345 laws ({label})",
                        "result": f"{s['exact']}/{s['laws']} exact ({s['exact'] / s['laws']:.1%})",
                        "date": date, "source": f"space/{f}"})
    lit = SPACE / "literature_discovery.md"
    if lit.exists():
        import re
        t = lit.read_text()
        m = re.search(r"\*\*(\d+)/(\d+) \(([\d.]+)%\)\*\*", t)
        rnd = re.search(r"Frequency-matched random pairs \| ([\d.]+)%", t)
        if m:
            out.append({"name": "Literature-based discovery, time-sliced (PubMed)",
                        "result": f"{m.group(1)}/{m.group(2)} predicted links later published ({m.group(3)}%) "
                                  f"vs {rnd.group(1) if rnd else '?'}% for random pairs",
                        "date": time.strftime("%Y-%m-%d", time.gmtime(lit.stat().st_mtime)),
                        "source": "space/literature_discovery.md"})
    return out


def run(reg: Registry | None = None, log=print) -> dict:
    reg = reg or Registry()
    log("gate self-test:")
    st = self_test(log)
    bm = benchmarks()
    claims = reg.claims()
    card = {"date": time.strftime("%Y-%m-%d"), "gate_self_test": st, "benchmarks": bm, "claims": reg.stats(),
            "discoveries": [c["id"] for c in claims if gate.is_discovery(c)]}
    (SPACE / "scorecard.json").write_text(json.dumps(card, indent=1) + "\n")

    L = ["# Euresis scorecard", "", f"Generated {card['date']} by `python -m euresis scorecard`.", "",
         "## 1. Verification gate self-test", "",
         f"**{st['passed']}/{st['total']}** known-true claims proved and known-false claims refuted.", "",
         "| Claim | Expected | Got | |", "|---|---|---|---|"]
    L += [f"| {r['claim']} | {r['expected']} | {r['got']} | {'✓' if r['pass'] else '✗'} |" for r in st["rows"]]
    L += ["", "## 2. Benchmarks", "", "| Benchmark | Result | Run | Source |", "|---|---|---|---|"]
    L += [f"| {b['name']} | {b['result']} | {b['date']} | `{b['source']}` |" for b in bm]
    L += ["", "## 3. Claims registry", "",
          "Status counts: " + ", ".join(f"{k}: {v}" for k, v in sorted(card["claims"].items())), "",
          "| Claim | Status | Verifier | Novelty |", "|---|---|---|---|"]
    order = {"proved": 0, "verified-numeric": 1, "unverified": 2, "candidate": 3, "refuted": 4}
    for c in sorted(claims, key=lambda c: order.get(c["status"], 9)):
        L.append(f"| {c['statement']} | **{gate.label(c)}** | {c.get('verifier') or '—'} | {c['novelty']} |")
    L += ["", "A claim counts as a **discovery** only when it is *proved* and not known. "
          f"Discoveries by that rule: **{len(card['discoveries'])}** — each still needs an expert literature check "
          "before it can be called new."]
    (SPACE / "scorecard.md").write_text("\n".join(L) + "\n")
    log(f"scorecard written to space/scorecard.md ({st['passed']}/{st['total']} self-test)")
    return card
