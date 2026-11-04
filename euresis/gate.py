"""The verification gate — no claim leaves Euresis without a machine check.

Each claim kind is routed to a verifier that can decide it:

| kind              | verifier                                        | best possible status |
|-------------------|-------------------------------------------------|----------------------|
| inequality        | Z3 (complete for real polynomial arithmetic)    | proved               |
|                   | + independent random-sampling cross-check       |                      |
| z3                | Z3                                              | proved               |
| physics-relation  | Z3 with exact square roots                      | proved               |
| identity          | SymPy simplification + numeric spot checks      | proved               |
| constant          | mpmath, two depths, ≥ 100 digits                | verified-numeric     |
| orbit             | kv validated ODE + Krawczyk (interval arith.)   | proved               |
| lean              | Lean 4 type checker                             | proved               |

Rules
* Only a verifier changes a claim's status.
* A failed *proof attempt* is not a refutation: Krawczyk or Z3 timing out gives
  ``unverified``; only a counterexample gives ``refuted``.
* High-precision agreement is evidence, never proof: ``verified-numeric``.
* ``is_discovery`` = proved AND novelty not ``known``. Everything else must be
  reported with its true status.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import sympy as sp

from .registry import ROOT, Registry

KV_DIR = ROOT / "data" / "external" / "verified" / "kv"
KV_REPO = "https://github.com/mskashi/kv.git"
ORBIT_SRC = ROOT / "euresis" / "proofs" / "threebody_proof2.cc"
ORBIT_BIN = ROOT / "data" / "bin" / "tbproof2"

SLOW_KINDS = {"orbit"}            # routed through the job queue by default


# ------------------------------------------------------------ verifiers
def _sym(expr: str, names=("a", "b", "c")):
    loc = {n: sp.Symbol(n, positive=True) for n in names}
    return sp.sympify(expr, locals=loc), [loc[n] for n in names]


def verify_inequality(p: dict) -> tuple[str, dict]:
    """P − mP ≥ k (Q − mQ) for all a, b, c > 0."""
    from . import theorems
    P, (a, b, c) = _sym(p["P"])
    Q, _ = _sym(p["Q"])
    k = sp.Rational(p["k"])
    mP, mQ = sp.nsimplify(P.subs({a: 1, b: 1, c: 1})), sp.nsimplify(Q.subs({a: 1, b: 1, c: 1}))
    # independent cross-check first: random points (log-uniform) must never violate the claim
    f = sp.lambdify((a, b, c), (P - mP) - k * (Q - mQ), "numpy")
    rng = np.random.default_rng(0)
    pts = np.exp(rng.uniform(-5, 5, (3, 200000)))
    with np.errstate(all="ignore"):
        vals = f(*pts)
    worst = float(np.nanmin(vals))
    if worst < -1e-9:
        i = int(np.nanargmin(vals))
        return "refuted", {"counterexample": pts[:, i].tolist(), "value": worst, "by": "random sampling"}
    verdict = theorems.prove(P, Q, mP, mQ, k)
    ev = {"z3": verdict, "sampling_min": worst, "samples": 200000}
    if verdict == "proved":
        if p.get("check_sharp", True):
            ev["sharp"] = theorems.prove(P, Q, mP, mQ, k * sp.Rational(1001, 1000), timeout_ms=20000) == "refuted"
        return "proved", ev
    if verdict == "refuted":
        return "refuted", ev
    return "unverified", ev


def verify_z3(p: dict) -> tuple[str, dict]:
    from .verify import prove_z3
    r = prove_z3(p["claim"], p.get("variables"), p.get("assumptions"), timeout_ms=p.get("timeout_ms", 60000))
    return {"proved": "proved", "refuted": "refuted"}.get(r["status"], "unverified"), r


def verify_physics_relation(p: dict) -> tuple[str, dict]:
    from .physics_theorems import z3_prove
    names = p["symbols"]
    loc = {n: sp.Symbol(n, positive=True) for n in names}
    claim = sp.sympify(p["claim"], locals=loc)
    asms = [sp.sympify(x, locals=loc) for x in p.get("assumptions", [])]
    r = z3_prove(claim, list(loc.values()), asms)
    return {"proved": "proved", "refuted": "refuted"}.get(r, "unverified"), {"z3": r, "domain": p.get("assumptions", [])}


def verify_identity(p: dict) -> tuple[str, dict]:
    names = p.get("symbols", [])
    loc = {n: sp.Symbol(n, positive=p.get("positive", True)) for n in names}
    lhs, rhs = sp.sympify(p["lhs"], locals=loc), sp.sympify(p["rhs"], locals=loc)
    syms = list(loc.values())
    f = sp.lambdify(syms, lhs - rhs, "mpmath")
    import mpmath as mp
    mp.mp.dps = 50
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(50):
        xs = [mp.mpf(float(np.exp(rng.uniform(-2, 2)))) for _ in syms]
        try:
            v = abs(f(*xs))
            scale = max(1, abs(sp.lambdify(syms, lhs, "mpmath")(*xs)))
            worst = max(worst, float(v / scale))
        except (ZeroDivisionError, ValueError):
            continue
    if worst > 1e-30:
        return "refuted", {"max_relative_difference": worst, "by": "50-digit evaluation at random points"}
    diff = sp.simplify(lhs - rhs)
    if diff == 0:
        return "proved", {"sympy": "lhs − rhs simplifies to 0", "numeric_max_rel_diff": worst}
    return "verified-numeric", {"sympy": f"did not simplify to 0 ({diff})", "numeric_max_rel_diff": worst}


_CONST = {"pi": "pi", "catalan": "catalan", "e": "e", "zeta3": "zeta(3)", "ln2": "log(2)", "euler": "euler"}


def _const_env(mp):
    return {"pi": mp.pi, "catalan": mp.catalan, "e": mp.e, "zeta": mp.zeta, "log": mp.log, "sqrt": mp.sqrt,
            "euler": mp.euler, "phi": mp.phi, "mpf": mp.mpf}


def verify_constant(p: dict) -> tuple[str, dict]:
    """Continued fraction a(0) + b(1)/(a(1) + b(2)/(a(2) + …)) equals `value`."""
    import mpmath as mp
    digits = int(p.get("digits", 100))
    mp.mp.dps = digits + 30
    n = sp.Symbol("n")
    A = sp.lambdify(n, sp.sympify(p["a"], locals={"n": n}), "mpmath")
    B = sp.lambdify(n, sp.sympify(p["b"], locals={"n": n}), "mpmath")

    def cf(depth):
        x = mp.mpf(A(depth))
        for k in range(depth - 1, -1, -1):
            x = A(k) + B(k + 1) / x
        return x
    d = int(p.get("depth", 2000))
    v1, v2 = cf(d), cf(2 * d)
    target = eval(p["value"], {"__builtins__": {}}, _const_env(mp))      # noqa: S307 — restricted namespace
    conv = float(-mp.log10(abs(v2 - v1) / abs(v2))) if v1 != v2 else float(mp.mp.dps)
    agree = float(-mp.log10(abs(v2 - target) / abs(target))) if v2 != target else float(mp.mp.dps)
    ev = {"digits_converged": round(conv, 1), "digits_agree": round(agree, 1), "depths": [d, 2 * d],
          "note": "numerical agreement is evidence, not proof"}
    if conv >= digits:                       # the fraction's value is known to `digits` digits
        return ("verified-numeric" if agree >= digits else "refuted"), ev
    return "unverified", ev


def ensure_orbit_prover(log=print) -> Path:
    """Fetch kv (header-only) and compile the three-body prover if needed."""
    if not (KV_DIR / "kv" / "interval.hpp").exists():
        log("fetching kv (validated numerics library)…")
        KV_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", KV_REPO, str(KV_DIR)], check=True)
    if not ORBIT_BIN.exists() or ORBIT_BIN.stat().st_mtime < ORBIT_SRC.stat().st_mtime:
        log("compiling three-body prover…")
        ORBIT_BIN.parent.mkdir(parents=True, exist_ok=True)
        cxx = shutil.which("g++") or shutil.which("c++")
        if not cxx:
            raise RuntimeError("a C++ compiler (g++) and Boost headers are required for orbit proofs")
        subprocess.run([cxx, "-O3", "-DNDEBUG", "-I", str(KV_DIR), str(ORBIT_SRC), "-o", str(ORBIT_BIN)], check=True)
    return ORBIT_BIN


def parse_orbit_output(out: str) -> dict:
    ev = {"log_tail": out.strip().splitlines()[-8:]}
    m = re.findall(r"x(\d) in \[([^,]+),([^\]]+)\]", out)
    if m:
        ev["box"] = {["p1", "p2", "tau"][int(i)]: [float(lo), float(hi)] for i, lo, hi in m}
    pm = re.search(r"period 2\*tau in \[([^,]+),([^\]]+)\]", out)
    if pm:
        ev["period"] = [float(pm.group(1)), float(pm.group(2))]
    nm = re.findall(r"\|\|Id - R F'\(I\)\|\|_inf <= ([0-9.eE+-]+)", out)
    if nm:
        ev["contraction_bounds"] = [float(x) for x in nm]
    return ev


def verify_orbit(p: dict, timeout_s: float | None = None, log=print) -> tuple[str, dict]:
    """Rigorous existence proof of a symmetric periodic three-body orbit (see euresis/proofs/README.md)."""
    binary = ensure_orbit_prover(log)
    args = [str(binary), repr(p["p1"]), repr(p["p2"]), repr(p["tau"]), str(p.get("order", 24))]
    t0 = time.time()
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout_s,
                           env={**os.environ, "KV_RADII": p.get("radii", "1e-9 1e-8 1e-10")})
    except subprocess.TimeoutExpired:
        return "unverified", {"reason": f"timeout after {timeout_s} s"}
    ev = parse_orbit_output(r.stdout + r.stderr)
    ev["seconds"] = round(time.time() - t0)
    if "PROVED: unique zero in box" in r.stdout:
        ev["theorem"] = ("There is exactly one (p1, p2, tau) in the box such that the solution is periodic with "
                         "period 2*tau; the motion is collision-free.")
        return "proved", ev
    ev["reason"] = "Krawczyk test did not succeed (this does not show the orbit is absent)"
    return "unverified", ev


def verify_lean(p: dict) -> tuple[str, dict]:
    from .verify import check_lean
    r = check_lean(p["source"], timeout=p.get("timeout", 600))
    return {"proved": "proved", "failed": "unverified"}.get(r["status"], "unverified"), r


VERIFIERS = {
    "inequality": ("z3+sampling", verify_inequality),
    "z3": ("z3", verify_z3),
    "physics-relation": ("z3-sqrt", verify_physics_relation),
    "identity": ("sympy+mpmath", verify_identity),
    "constant": ("mpmath", verify_constant),
    "orbit": ("kv-krawczyk", verify_orbit),
    "lean": ("lean4", verify_lean),
}


# ------------------------------------------------------------------ gate
def check(reg: Registry, cid: str, log=print, **kw) -> str:
    c = reg.get(cid)
    if c is None:
        raise KeyError(cid)
    name, fn = VERIFIERS[c["kind"]]
    try:
        status, ev = fn(c["payload"], **kw) if kw else fn(c["payload"])
    except Exception as e:                       # a crashing verifier proves nothing
        status, ev = "unverified", {"error": f"{type(e).__name__}: {e}"}
    reg.set_status(cid, status, name, ev)
    log(f"  [{status:16s}] {c['statement'][:90]}  ({name})")
    return status


def run(reg: Registry | None = None, include_slow=False, recheck=False, log=print) -> dict:
    """Send every unchecked claim through its verifier; slow ones go to the job queue."""
    reg = reg or Registry()
    todo = [c for c in reg.claims() if recheck or c["status"] in ("candidate", "unverified")]
    queued = 0
    for c in todo:
        if c["kind"] in SLOW_KINDS and not include_slow:
            pending = [j for j in reg.jobs() if j["kind"] == "gate" and j["args"].get("claim") == c["id"]
                       and j["state"] in ("queued", "running")]
            if not pending:
                reg.submit("gate", {"claim": c["id"]})
                queued += 1
            continue
        check(reg, c["id"], log=log)
    if queued:
        log(f"  {queued} slow claim(s) queued — run `python -m euresis jobs work` to process them")
    return reg.stats()


def is_discovery(c: dict) -> bool:
    return c["status"] == "proved" and not c.get("novelty", "").startswith("known")


def label(c: dict) -> str:
    """The honest one-line label for a claim."""
    s = c["status"]
    if s == "proved":
        nov = c.get("novelty", "not checked")
        return "proved; " + ("already known" if nov.startswith("known") else f"novelty: {nov}")
    return {"verified-numeric": "numerically verified, not proved", "refuted": "false",
            "unverified": "not verified", "candidate": "not yet checked"}[s]


def ingest_orbit_log(reg: Registry, cid: str, text: str, args: dict | None = None) -> str:
    """Record a prover run made outside the queue (same binary, same acceptance rule as verify_orbit)."""
    ev = parse_orbit_output(text)
    if args:
        ev["run_args"] = args
    if "PROVED: unique zero in box" in text:
        ev["theorem"] = ("There is exactly one (p1, p2, tau) in the box such that the solution is periodic with "
                         "period 2*tau; the motion is collision-free.")
        status = "proved"
    else:
        ev["reason"] = "Krawczyk test did not succeed (this does not show the orbit is absent)"
        status = "unverified"
    reg.set_status(cid, status, VERIFIERS["orbit"][0], ev)
    for j in reg.jobs():                         # the queued job for this claim is now redundant
        if j["kind"] == "gate" and j["args"].get("claim") == cid and j["state"] == "queued":
            reg.finish_job(j["id"], result={"status": status, "via": "ingested log"})
    return status
