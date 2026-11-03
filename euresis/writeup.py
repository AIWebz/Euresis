"""Write-ups for expert review.

For every claim that passed the gate (proved, or numerically verified) and is not
known, produce a short self-contained note an expert can check in minutes:
statement, exact status, how it was verified, the evidence, what was and was not
searched for novelty, and the commands that reproduce it. Markdown for reading,
LaTeX for posting as a preprint.

    python -m euresis writeup            # → space/writeups/<claim-id>.{md,tex}
"""
from __future__ import annotations

import json
from pathlib import Path

from . import gate
from .registry import ROOT, Registry

OUT = ROOT / "space" / "writeups"

METHOD = {
    "inequality": "Found by numerical minimisation of the ratio (P − min P)/(Q − min Q) and snapped to an exact "
                  "rational. Proved with the Z3 SMT solver, which decides real polynomial inequalities completely: "
                  "both sides are homogeneous of degree 0, so a = 1 without loss of generality, denominators are "
                  "cleared and shown positive, and the negation of the numerator inequality is shown unsatisfiable. "
                  "Cross-checked independently at 200 000 random points.",
    "z3": "Proved with the Z3 SMT solver (the negation is unsatisfiable).",
    "physics-relation": "Proved with the Z3 SMT solver; each square root s = √x is encoded exactly as s ≥ 0, s² = x.",
    "identity": "SymPy simplifies lhs − rhs to 0; confirmed at 50 random points with 50-digit arithmetic.",
    "constant": "Found by a Ramanujan-Machine-style search over polynomial continued fractions; the fraction is "
                "evaluated with mpmath at two depths (to show convergence) and compared with the closed form. "
                "This is numerical evidence, not a proof.",
    "orbit": "Computer-assisted proof. With r1 = (−1,0), r2 = (1,0), r3 = 0, v1 = v2 = (p1,p2), v3 = −2(p1,p2), the "
             "solution is reversible. If at time τ body 3 is at the origin and (v1 − v2)·r1 = 0, then (since P = 0 "
             "and L = 0 are conserved) the state is again symmetric and the orbit is periodic with period 2τ. The "
             "three equations in (p1, p2, τ) are solved by the Krawczyk method: the flow and its derivatives are "
             "enclosed rigorously with the kv library (Taylor models with affine arithmetic, variational equations "
             "integrated in the same validated solve). K(I) ⊂ int(I) proves a unique solution in the box I. The "
             "successful validated integration also proves the motion is collision-free on [0, τ].",
    "lean": "Type-checked by the Lean 4 kernel.",
}

REPRO = {
    "orbit": "g++ -O3 -DNDEBUG -I data/external/verified/kv euresis/proofs/threebody_proof2.cc -o tbproof2\n"
             "KV_RADII=\"1e-9 1e-8\" ./tbproof2 {p1} {p2} {tau} 24",
}


def _md(c: dict) -> str:
    ev = c.get("evidence") or {}
    repro = REPRO.get(c["kind"], "python -m euresis gate --recheck   # re-runs every verifier").format(**c["payload"])
    lines = [f"# {c['statement']}", "",
             f"*Claim `{c['id']}` · source: `euresis/{c['source']}` · status: **{gate.label(c)}***", "",
             "## Statement", "", c["statement"], "", "Exact payload checked by the verifier:", "",
             "```json", json.dumps(c["payload"], indent=1), "```", "",
             "## Method", "", METHOD.get(c["kind"], ""), "",
             "## Evidence", "", "```json", json.dumps(ev, indent=1, default=str), "```", "",
             "## Novelty", "", f"{c['novelty']}.", "",
             "Before this is called new, an expert should check the literature this environment could not reach.",
             "", "## Reproduce", "", "```bash", repro, "```", ""]
    return "\n".join(lines)


def _tex_escape(s: str) -> str:
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return s


def _tex(c: dict) -> str:
    ev = json.dumps(c.get("evidence") or {}, indent=1, default=str)
    return "\n".join([
        "% compile with xelatex or lualatex (the text contains Unicode math symbols)",
        r"\documentclass[11pt]{article}", r"\usepackage{amsmath,amssymb}", r"\usepackage{fontspec}",
        r"\setmainfont{DejaVu Serif}", r"\setmonofont{DejaVu Sans Mono}", r"\usepackage[margin=1in]{geometry}",
        r"\title{" + _tex_escape(c["statement"]) + "}", r"\author{Euresis (automated discovery system)}",
        r"\date{\today}", r"\begin{document}", r"\maketitle",
        r"\paragraph{Status.} " + _tex_escape(gate.label(c)) + ".",
        r"\section{Method}", _tex_escape(METHOD.get(c["kind"], "")),
        r"\section{Evidence}", r"\begin{verbatim}", ev, r"\end{verbatim}",
        r"\section{Exact claim}", r"\begin{verbatim}", json.dumps(c["payload"], indent=1), r"\end{verbatim}",
        r"\section{Novelty}", _tex_escape(c["novelty"]) + ".",
        r"\end{document}", ""])


def run(reg: Registry | None = None, log=print) -> list[Path]:
    reg = reg or Registry()
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for c in reg.claims():
        if c["status"] not in ("proved", "verified-numeric") or c["novelty"].startswith("known"):
            continue
        (OUT / f"{c['id']}.md").write_text(_md(c))
        (OUT / f"{c['id']}.tex").write_text(_tex(c))
        written.append(OUT / f"{c['id']}.md")
    idx = ["# Write-ups for expert review", "",
           "Claims that passed the verification gate and are not known to Euresis. "
           "Each note is self-contained and lists exactly what was and was not checked.", "",
           "| Claim | Status | Note |", "|---|---|---|"]
    for p in written:
        c = reg.get(p.stem)
        idx.append(f"| {c['statement']} | {gate.label(c)} | [{p.name}]({p.name}) · [tex]({p.stem}.tex) |")
    (OUT / "README.md").write_text("\n".join(idx) + "\n")
    log(f"{len(written)} write-ups in space/writeups/")
    return written
