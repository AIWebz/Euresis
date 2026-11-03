"""Bring the results of Euresis' discovery engines into the claims registry.

Each engine writes human-readable reports in ``space/``; this module turns its
claims into exact, machine-checkable payloads so the verification gate can
re-check every one of them independently.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import sympy as sp

from .registry import ROOT, Registry

SPACE = ROOT / "space"


# ---------------------------------------------------------------- inequalities
def _library_expr(name: str):
    from .theorems import LIBRARY
    if name in LIBRARY:
        return LIBRARY[name]
    m = re.fullmatch(r"\((.+)\)·\((.+)\)", name)
    if m and m.group(1) in LIBRARY and m.group(2) in LIBRARY:
        return LIBRARY[m.group(1)] * LIBRARY[m.group(2)]
    return None


def inequalities(reg: Registry) -> int:
    path = SPACE / "theorems.md"
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("P", "---"):
            continue
        P, Q = _library_expr(cells[0]), _library_expr(cells[1])
        if P is None or Q is None:
            continue
        novelty = ("known (very likely: both sides classical)" if "already known" in cells[4]
                   else "not among the classical inequalities Euresis knows; inequality literature not searched")
        reg.add("inequality",
                f"For all a,b,c > 0:  [{cells[0]}] − min  ≥  {cells[2]} · ([{cells[1]}] − min)",
                {"P": str(P), "Q": str(Q), "k": cells[2]}, source="theorems.py", novelty=novelty)
        n += 1
    return n


# ------------------------------------------------------------ continued fractions
_REPL = [("G (Catalan)", "catalan"), ("π", "pi"), ("−", "-"), ("·", "*"), ("²", "**2"), ("³", "**3"),
         ("^", "**"), ("ln 2", "log(2)"), ("ζ(3)", "zeta(3)")]


def _pretty_to_sympy(s: str) -> str:
    for a, b in _REPL:
        s = s.replace(a, b)
    s = re.sub(r"√(\d+)", r"sqrt(\1)", s)
    s = re.sub(r"(\d)\s*n", r"\1*n", s)            # 3n → 3*n
    s = re.sub(r"(\d)\s*\(", r"\1*(", s)
    return s


def continued_fractions(reg: Registry) -> int:
    path = SPACE / "novelty_search.md"
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text().splitlines():
        if "passes every available novelty check" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        const, closed, a, b = cells[1], cells[2], cells[3], cells[4]
        payload = {"a": _pretty_to_sympy(a), "b": _pretty_to_sympy(b), "value": _pretty_to_sympy(closed),
                   "digits": 100}
        reg.add("constant", f"{const}: continued fraction a(n) = {a}, b(n) = {b} equals {closed}", payload,
                source="novelty_math.py",
                novelty="not in classical families or the Ramanujan Machine's published search domains; "
                        "LIReC/OEIS/arXiv not checked")
        n += 1
    return n


# --------------------------------------------------------------- physics laws
def physics_relations(reg: Registry) -> int:
    path = SPACE / "physics_theorems.md"
    if not path.exists() or "Relativistic kinetic energy ≤ 1 × Total relativistic energy" not in path.read_text():
        return 0
    reg.add("physics-relation", "Relativistic kinetic energy ≤ total relativistic energy (all m, c > 0, 0 < v < c)",
            {"claim": "m*c**2/sqrt(1 - v**2/c**2) >= m*c**2*(1/sqrt(1 - v**2/c**2) - 1)", "symbols": ["c", "m", "v"]},
            source="physics_theorems.py", novelty="known (E = K + mc², so K ≤ E)")
    return 1


# ---------------------------------------------------------------------- orbits
def orbits(reg: Registry) -> int:
    path = SPACE / "threebody" / "orbits.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text())
    n = 0
    for o in data["orbits"]:
        name = o.get("catalog")
        # the prover handles orbits whose symmetric point at T/2 has body 3 at the centre;
        # the plain figure-eight start reaches it at T/3 (body 2), so it is not routed here.
        if name == "I.A1":
            continue
        novelty = (f"known (Li & Liao 2017 catalogue: {name})" if name else
                   "not in Li & Liao 2017 catalogue (695 families); newer catalogues "
                   "(e.g. Hristov et al. 2022–2025) not checked — arXiv unreachable here")
        reg.add("orbit", f"Periodic equal-mass three-body orbit with v = ({o['v1']:.10f}, {o['v2']:.10f}), "
                         f"T ≈ {o['T']:.6f}, T* ≈ {o['Tstar']:.3f}",
                {"p1": round(o["v1"], 10), "p2": round(o["v2"], 10), "tau": round(o["T"] / 2, 6)},
                source="threebody.py", novelty=novelty)
        n += 1
    return n


def run(reg: Registry | None = None, log=print) -> dict:
    reg = reg or Registry()
    counts = {"inequalities": inequalities(reg), "continued fractions": continued_fractions(reg),
              "physics relations": physics_relations(reg), "orbits": orbits(reg)}
    log(f"collected: {counts}")
    return counts
