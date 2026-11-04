"""Physics discovery loop: sharp, machine-proved bounds between physical quantities.

Each physical system is a *family* of dimensionless quantities that depend on
one physical variable over its physical domain (β = v/c in special relativity,
eccentricity e for Kepler orbits, temperature ratio τ = Tc/Th for heat engines).

Each round:
  1. **Propose** — the local 14B model (Qwen3-14B) suggests new physically
     meaningful quantities for a family, with what they mean. (Euresis' seed
     library is used alone when the model is not installed.)
  2. **Validate** — Euresis checks each exactly: parses, only the family's
     variable, built from + − × ÷ powers and square roots (so the prover can
     decide it), finite and positive on the domain, and not an affine
     combination or product of known quantities.
  3. **Discover** — for every pair (f, g) Euresis computes inf and sup of f/g
     over the domain and snaps them to exact rationals, giving candidate laws
     f ≥ k·g or f ≤ K·g.
  4. **Prove** — each candidate goes to the verification gate as a
     physics-relation with its domain (Z3 with exact square roots). Sharpness:
     a constant 10⁻⁶ tighter must be refuted.
  5. **Record** — a *discovery* is proved, sharp, not a known result, and not a
     consequence of two bounds already proved. Novelty against the literature
     is labelled unchecked (arXiv is unreachable from this environment).

Runs until `data/STOP` exists or the segment's time budget ends; resumes from
`space/physics_discovery_state.json`.
"""
from __future__ import annotations

import json
import random
import re
import time
from fractions import Fraction

import numpy as np
import sympy as sp

from . import gate
from .registry import ROOT, Registry

STATE = ROOT / "space" / "physics_discovery_state.json"
LOG = ROOT / "space" / "physics_discovery_log.md"
STOP = ROOT / "data" / "STOP"

FAMILIES = {
    "relativity": {
        "var": "b", "meaning": "b = v/c, the speed as a fraction of the speed of light", "domain": ["b < 1"],
        "quantities": {
            "Lorentz factor γ": "1/sqrt(1 - b**2)",
            "relativistic kinetic energy / mc²": "1/sqrt(1 - b**2) - 1",
            "classical kinetic energy / mc²": "b**2/2",
            "relativistic momentum / (mc)": "b/sqrt(1 - b**2)",
            "relativistic Doppler factor (approaching source)": "sqrt((1 + b)/(1 - b))",
            "time-dilation factor 1/γ": "sqrt(1 - b**2)",
            "relative speed of two bodies each at speed b, head-on (velocity addition) / c": "2*b/(1 + b**2)",
            "kinetic energy / (momentum × c)": "(1 - sqrt(1 - b**2))/b",
        }},
    "kepler": {
        "var": "e", "meaning": "e = eccentricity of a bound Kepler orbit (semi-major axis a = 1, GM = 1)",
        "domain": ["e < 1"],
        "quantities": {
            "perihelion distance / a": "1 - e",
            "aphelion distance / a": "1 + e",
            "perihelion speed / circular speed at a": "sqrt((1 + e)/(1 - e))",
            "aphelion speed / circular speed at a": "sqrt((1 - e)/(1 + e))",
            "semi-minor axis / a": "sqrt(1 - e**2)",
            "semi-latus rectum / a": "1 - e**2",
            "time-averaged distance / a": "1 + e**2/2",
        }},
    "heat engines": {
        "var": "t", "meaning": "t = Tc/Th, cold-to-hot reservoir temperature ratio", "domain": ["t < 1"],
        "quantities": {
            "Carnot efficiency": "1 - t",
            "Curzon–Ahlborn efficiency (endoreversible engine at maximum power)": "1 - sqrt(t)",
            "low-dissipation engine efficiency at maximum power, upper bound (Esposito et al.)": "(1 - t)/(1 + t)",
            "Carnot refrigerator coefficient of performance": "t/(1 - t)",
            "Carnot heat pump coefficient of performance": "1/(1 - t)",
        }},
}

# bounds the physics literature already has (family, f, g, direction) — rediscoveries, not discoveries
KNOWN = {
    ("relativity", "relativistic kinetic energy / mc²", "classical kinetic energy / mc²", "lower"):
        "relativistic KE exceeds classical KE",
    ("relativity", "Lorentz factor γ", "relativistic kinetic energy / mc²", "lower"): "E = K + mc²",
    ("heat engines", "Curzon–Ahlborn efficiency (endoreversible engine at maximum power)", "Carnot efficiency", "lower"):
        "η_CA ≥ η_C/2 (Esposito et al. 2010)",
    ("heat engines", "Curzon–Ahlborn efficiency (endoreversible engine at maximum power)", "Carnot efficiency", "upper"):
        "η_CA ≤ η_C",
    ("heat engines", "low-dissipation engine efficiency at maximum power, upper bound (Esposito et al.)",
     "Carnot efficiency", "lower"): "η_C/(2 − η_C) ≥ η_C/2 (Esposito et al. 2010)",
}


# ------------------------------------------------------------------ state
def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"families": {k: dict(v["quantities"]) for k, v in FAMILIES.items()}, "rejected": [], "tried": [],
            "edges": [], "rounds": 0, "discoveries": [], "rediscoveries": []}


def save_state(st: dict):
    STATE.write_text(json.dumps(st, indent=1) + "\n")


def log(msg: str, echo=print):
    echo(msg)
    with LOG.open("a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


def _grid():
    lo = np.logspace(-6, np.log10(0.5), 4000)
    return np.unique(np.concatenate([lo, 1 - lo]))


GRID = _grid()


# ------------------------------------------------------------- validation
def _allowed(E: sp.Expr) -> bool:
    for node in sp.preorder_traversal(E):
        if isinstance(node, sp.Function) or node.is_Function:
            return False
        if node.is_Pow and not sp.Rational(node.exp).q in (1, 2):
            return False
    return True


def validate(fam: str, expr: str, known: dict) -> tuple[sp.Expr | None, str]:
    v = sp.Symbol(FAMILIES[fam]["var"], positive=True)
    try:
        E = sp.sympify(expr.replace("^", "**"), locals={v.name: v})
    except Exception:
        return None, "does not parse"
    if not isinstance(E, sp.Expr) or E.free_symbols != {v}:
        return None, f"must depend on {v} only"
    try:
        if not _allowed(E):
            return None, "only + − × ÷, integer powers and square roots (so the prover can decide it)"
    except (TypeError, ValueError):
        return None, "only rational exponents allowed"
    f = sp.lambdify(v, E, "numpy")
    with np.errstate(all="ignore"):
        vals = np.asarray(f(GRID), float)
    if not np.all(np.isfinite(vals)) or np.iscomplexobj(vals):
        return None, "not finite on the whole physical domain"
    if vals.min() <= 0:
        return None, "not positive on the physical domain"
    K = {n: np.asarray(sp.lambdify(v, sp.sympify(s, locals={v.name: v}), "numpy")(GRID), float) for n, s in known.items()}
    one = np.ones_like(vals)
    sel = slice(None, None, 37)
    for i, ni in enumerate(K):
        for nj in [None] + list(K)[i:]:
            A = np.stack([one, K[ni]] + ([K[nj]] if nj and nj != ni else []), 1)[sel]
            coef, *_ = np.linalg.lstsq(A, vals[sel], rcond=None)
            if np.abs(A @ coef - vals[sel]).max() < 1e-9 * max(1, np.abs(vals).max()):
                return None, f"affine combination of known quantities ({ni}{', ' + nj if nj and nj != ni else ''})"
            if nj is None:
                r = vals[sel] * K[ni][sel]
                if r.max() - r.min() < 1e-9 * max(1, abs(r).max()):
                    return None, f"reciprocal of a known quantity ({ni})"
            else:
                for label, other in (("product", K[ni] * K[nj]), ("ratio", K[ni] / K[nj]), ("ratio", K[nj] / K[ni])):
                    r = vals[sel] / other[sel]
                    if r.max() - r.min() < 1e-9 * max(1, abs(r).max()):
                        return None, f"{label} of known quantities ({ni}, {nj})"
    return E, "ok"


# --------------------------------------------------------------- proposals
def propose_llm(fam: str, st: dict, n: int = 4, echo=print) -> list[dict]:
    from . import local_llm
    F = FAMILIES[fam]
    known = st["families"][fam]
    rej = [r for r in st["rejected"] if r.get("family") == fam][-8:]
    msg = (f"Physical system: {fam}. Variable: {F['meaning']}; physical domain 0 < {F['var']} < 1.\n"
           "Known dimensionless quantities (name: SymPy expression):\n"
           + "\n".join(f"  {k}: {v}" for k, v in known.items())
           + f"\n\nPropose {n} OTHER physically meaningful dimensionless quantities of this system, as functions of "
           f"{F['var']} only. Use only + - * /, integer powers (**) and sqrt. Each must be positive and finite for "
           f"0 < {F['var']} < 1 and must not be a simple sum or product of the known ones.\n"
           + ("Rejected before (reason in brackets):\n" + "\n".join(f"  {r['expr']} [{r['why']}]" for r in rej) + "\n"
              if rej else "")
           + 'Reply with JSON only: [{"name": "...", "expr": "..."}, ...]')
    r = local_llm.complete("You are the physics idea generator of Euresis. You propose; a theorem prover decides "
                           "what is true. Reply with JSON only.", [{"role": "user", "content": msg}],
                           think=False, max_tokens=700, temperature=0.8, log=echo)
    items = parse_items(r["text"] or r["raw"])
    if not items:
        log(f"model reply could not be parsed ({fam}): {(r['raw'] or '')[:300]!r}", echo)
    echo(f"  model proposed {len(items)} quantities for {fam} in {r['seconds']} s")
    return items[:n]


def parse_items(text: str) -> list[dict]:
    """JSON list of {name, expr}; falls back to pulling out each name/expr pair if the JSON is malformed."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    m = re.search(r"\[.*\]", text, re.S)
    if m:
        try:
            items = json.loads(m.group(0))
            items = [x for x in items if isinstance(x, dict) and isinstance(x.get("expr"), str)]
            if items:
                return items
        except json.JSONDecodeError:
            pass
    pairs = re.findall(r'"name"\s*:\s*"([^"]*)"\s*,\s*"expr"\s*:\s*"([^"]*)"', text)
    return [{"name": n, "expr": e} for n, e in pairs]


# ---------------------------------------------------------------- bounds
def _snap(x: float) -> sp.Rational | None:
    fr = Fraction(x).limit_denominator(64)
    if abs(float(fr) - x) <= 2e-5 * max(1.0, abs(x)) and fr != 0:     # the gate then decides exactly
        return sp.Rational(fr.numerator, fr.denominator)
    return None


def candidate_bounds(fam: str, fn: str, gn: str, exprs: dict):
    v = sp.Symbol(FAMILIES[fam]["var"], positive=True)
    f = sp.sympify(exprs[fn], locals={v.name: v})
    g = sp.sympify(exprs[gn], locals={v.name: v})
    with np.errstate(all="ignore"):
        r = np.asarray(sp.lambdify(v, f / g, "numpy")(GRID), float)
    r = r[np.isfinite(r)]
    if r.size < GRID.size // 2 or r.max() - r.min() < 1e-9 * max(1, abs(r).max()):
        return []                                     # undefined or a constant ratio (an identity)
    # only lower bounds f ≥ k·g: an upper bound f ≤ K·g is the lower bound g ≥ (1/K)·f of the swapped pair
    with np.errstate(all="ignore"):
        full = np.asarray(sp.lambdify(v, f / g, "numpy")(GRID), float)
    i = int(np.nanargmin(full))
    val = float(full[i])
    if not (0 < val < 1e6):
        return []
    k = _snap(val)
    if k is None:
        return []
    x = float(GRID[i])
    interior = 1e-3 < x < 1 - 1e-3 and 0 < i < len(GRID) - 1 and full[i - 1] > val and full[i + 1] > val
    return [("lower", k, f, g, v, interior, x)]


def prove_bound(fam, kind, k, f, g, v) -> tuple[str, dict, bool]:
    domain = FAMILIES[fam]["domain"]
    claim = f"{f} >= {k}*({g})" if kind == "lower" else f"{f} <= {k}*({g})"
    payload = {"claim": claim, "symbols": [v.name], "assumptions": domain}
    status, ev = gate.verify_physics_relation(payload)
    sharp = False
    if status == "proved":
        k2 = k * (1 + sp.Rational(1, 10 ** 6)) if kind == "lower" else k * (1 - sp.Rational(1, 10 ** 6))
        tighter = f"{f} >= {k2}*({g})" if kind == "lower" else f"{f} <= {k2}*({g})"
        sharp = gate.verify_physics_relation({"claim": tighter, "symbols": [v.name], "assumptions": domain})[0] == "refuted"
    return status, payload, sharp


def implied(st: dict, fam: str, fn: str, gn: str, kind: str, k) -> str:
    """Follows from two proved bounds f ≥ k1·h, h ≥ k2·g (or the upper-bound analogue)?"""
    E = {(e["f"], e["g"], e["kind"]): sp.Rational(e["k"]) for e in st["edges"] if e["family"] == fam}
    if (fn, gn, kind) in E and ((E[(fn, gn, kind)] >= k) if kind == "lower" else (E[(fn, gn, kind)] <= k)):
        return "a bound at least as strong is already proved"
    for (x, h, kd), k1 in E.items():
        if x == fn and kd == kind and (h, gn, kind) in E:
            kk = k1 * E[(h, gn, kind)]
            if (kk >= k) if kind == "lower" else (kk <= k):
                return f"follows from bounds through '{h}'"
    return ""


# ---------------------------------------------------------------- one round
def run_round(st: dict, reg: Registry, use_llm: bool, echo=print, max_pairs: int = 16) -> list[dict]:
    st["rounds"] += 1
    fams = list(FAMILIES)
    fam = fams[(st["rounds"] - 1) % len(fams)]
    log(f"round {st['rounds']}: {fam}", echo)
    exprs = st["families"][fam]
    new = {}
    if use_llm:
        for item in propose_llm(fam, st, echo=echo):
            E, why = validate(fam, item["expr"], {**exprs, **new})
            name = str(item.get("name") or item["expr"])[:90]
            if E is None:
                st["rejected"].append({"family": fam, "expr": item["expr"][:100], "why": why})
                echo(f"    rejected: {name}: {item['expr'][:60]}  [{why}]")
            elif name in exprs or name in new:
                continue
            else:
                new[name] = str(E)
                echo(f"    accepted: {name} = {E}")
    exprs.update(new)
    names = list(exprs)
    pairs = [(x, y) for x in names for y in names if x != y and f"{fam}|{x}|{y}" not in st["tried"]]
    pairs.sort(key=lambda p: (p[0] not in new and p[1] not in new, random.Random(st["rounds"]).random()))
    found = []
    for fn, gn in pairs[:max_pairs]:
        st["tried"].append(f"{fam}|{fn}|{gn}")
        for kind, k, f, g, v, interior, x_eq in candidate_bounds(fam, fn, gn, exprs):
            status, payload, sharp = prove_bound(fam, kind, k, f, g, v)
            if status != "proved" or not sharp:
                continue
            rel = "≥" if kind == "lower" else "≤"
            where = f"equality at {v} ≈ {x_eq:.6g}" if interior else f"tight only in the limit {v} → {round(x_eq)}"
            stmt = f"[{fam}] {fn} {rel} {k} × {gn}   for 0 < {v} < 1 ({where})"
            known = KNOWN.get((fam, fn, gn, kind))
            chain = implied(st, fam, fn, gn, kind, k)
            cid = reg.add("physics-relation", stmt, payload, source=f"physics_discover round {st['rounds']}")
            gate.check(reg, cid, log=lambda *x: None)            # the registry's own, independent gate run
            if reg.get(cid)["status"] != "proved":
                continue
            st["edges"].append({"family": fam, "f": fn, "g": gn, "kind": kind, "k": str(k)})
            if known:
                reg.set_novelty(cid, f"known ({known})")
                st["rediscoveries"].append({"claim": cid, "statement": stmt, "known": known})
                echo(f"    rediscovered known law: {stmt}  ({known})")
            elif chain:
                reg.set_novelty(cid, f"follows from proved bounds: {chain}")
                echo(f"    proved but implied: {stmt}")
            elif not interior:
                reg.set_novelty(cid, "asymptotic comparison (tight only at the edge of the domain) — proved, "
                                     "not counted as a discovery")
                echo(f"    proved (asymptotic only): {stmt}")
            else:
                reg.set_novelty(cid, "not a known result in Euresis' knowledge; not implied by proved bounds; "
                                     "physics literature unchecked (arXiv unreachable from this environment)")
                rec = {"claim": cid, "statement": stmt, "round": st["rounds"]}
                st["discoveries"].append(rec)
                found.append(rec)
                log(f"DISCOVERY (proved, sharp to 1e-6): {stmt}  [{cid}]", echo)
    return found


def run(minutes: float = 100.0, use_llm: bool | None = None, echo=print) -> dict:
    from . import local_llm
    if use_llm is None:
        use_llm = local_llm.available()
    st, reg = load_state(), Registry()
    t0 = time.time()
    log(f"segment start (budget {minutes:.0f} min; model: {'Qwen3-14B' if use_llm else 'none'}; "
        f"{len(st['discoveries'])} discoveries so far)", echo)
    while time.time() - t0 < minutes * 60:
        if STOP.exists():
            log("STOP file found — stopping as instructed", echo)
            break
        try:
            run_round(st, reg, use_llm, echo=echo)
        except Exception as e:
            log(f"round failed: {type(e).__name__}: {e}", echo)
        save_state(st)
        if not use_llm and all(f"{fam}|{x}|{y}" in st["tried"] for fam in FAMILIES
                               for x in st["families"][fam] for y in st["families"][fam] if x != y):
            log("seed library exhausted and no model to propose new quantities", echo)
            break
    log(f"segment end: {st['rounds']} rounds, {len(st['discoveries'])} discoveries, "
        f"{len(st['rediscoveries'])} known laws rediscovered", echo)
    return st
