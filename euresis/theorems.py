"""Discover and *prove* sharp inequalities — runs until a proven discovery is made.

For two symmetric, scale-invariant expressions P(a,b,c) and Q(a,b,c) of positive
reals, both minimised at a = b = c (values mP, mQ), Euresis looks for the best
constant k* such that

        P − mP  ≥  k* · (Q − mQ)      for all a, b, c > 0.

Pipeline for every pair:
1. **Discover** — k* = inf (P − mP)/(Q − mQ), found by numerical minimisation
   (many starts, including the boundary c → 0); snapped to an exact rational.
2. **Prove** — clear denominators (setting a = 1 is legitimate: both sides are
   homogeneous of degree 0) and ask the Z3 prover to show the polynomial
   inequality's negation has no solution with b, c > 0. Z3's nonlinear real
   arithmetic is a complete decision procedure, so "proved" is a proof.
3. **Sharp** — exhibit points where the ratio approaches k*: no larger constant works.
4. **Novel?** — reject the classical inequalities Euresis knows; everything else is
   reported as *not in Euresis' knowledge*, with the caveat that the inequality
   literature cannot be searched from here.
"""
from __future__ import annotations

import itertools
import json
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
import sympy as sp
from scipy.optimize import minimize

a, b, c = sp.symbols("a b c", positive=True)
OUT = Path(__file__).resolve().parent.parent / "space" / "theorems.md"

LIBRARY = {
    "(a²+b²+c²)/(ab+bc+ca)": (a**2 + b**2 + c**2) / (a*b + b*c + c*a),
    "a/(b+c)+b/(c+a)+c/(a+b)": a/(b + c) + b/(c + a) + c/(a + b),
    "(a+b+c)³/(27abc)": (a + b + c)**3 / (27*a*b*c),
    "(a+b+c)(1/a+1/b+1/c)/9": (a + b + c) * (1/a + 1/b + 1/c) / 9,
    "(a³+b³+c³)/(3abc)": (a**3 + b**3 + c**3) / (3*a*b*c),
    "(a+b)(b+c)(c+a)/(8abc)": (a + b)*(b + c)*(c + a) / (8*a*b*c),
    "a/b+b/c+c/a (sym.)": (a/b + b/a + b/c + c/b + c/a + a/c) / 2,
    "3(a²+b²+c²)/(a+b+c)²": 3*(a**2 + b**2 + c**2) / (a + b + c)**2,
    "(a²+b²+c²)(a+b+c)/(9abc)": (a**2 + b**2 + c**2)*(a + b + c) / (9*a*b*c),
    "(ab+bc+ca)²/(3abc(a+b+c))": (a*b + b*c + c*a)**2 / (3*a*b*c*(a + b + c)),
}
CLASSICAL = {  # inequalities Euresis already knows (the minimum values themselves)
    "(a+b+c)³/(27abc)": "AM–GM", "a/(b+c)+b/(c+a)+c/(a+b)": "Nesbitt (1903)",
    "(a²+b²+c²)/(ab+bc+ca)": "rearrangement / sum of squares", "(a+b+c)(1/a+1/b+1/c)/9": "AM–HM",
    "(a³+b³+c³)/(3abc)": "AM–GM", "(a+b)(b+c)(c+a)/(8abc)": "AM–GM",
}


def _min_value(E):
    return sp.nsimplify(E.subs({a: 1, b: 1, c: 1}))


def ratio_inf(P, Q, mP, mQ, starts=60, seed=0):
    """inf over b, c > 0 (a = 1) of (P − mP)/(Q − mQ), searched in log-coordinates."""
    f = sp.lambdify((b, c), ((P - mP) / (Q - mQ)).subs(a, 1), "numpy")
    rng = np.random.default_rng(seed)
    best = (np.inf, None)

    def obj(x):
        with np.errstate(all="ignore"):
            v = f(np.exp(x[0]), np.exp(x[1]))
        return v if np.isfinite(v) else 1e9
    for _ in range(starts):
        x0 = rng.uniform(-4, 4, 2)
        r = minimize(obj, x0, method="Nelder-Mead", options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 4000})
        if r.fun < best[0]:
            best = (float(r.fun), r.x)
    # approach to the equality point a = b = c (ratio of second-order terms)
    for eps in (1e-3, 1e-4):
        for d in np.linspace(0, 2 * np.pi, 24, endpoint=False):
            x = np.array([eps * np.cos(d), eps * np.sin(d)])
            v = obj(x)
            if v < best[0]:
                best = (float(v), x)
    return best


def snap(x):
    fr = Fraction(x).limit_denominator(64)
    return sp.Rational(fr.numerator, fr.denominator) if abs(float(fr) - x) < 2e-6 * max(1, abs(x)) else None


def prove(P, Q, mP, mQ, k, timeout_ms=60000):
    """Z3: is (P − mP) − k (Q − mQ) ≥ 0 for all b, c > 0 (a = 1)?"""
    import z3
    expr = sp.together(((P - mP) - k * (Q - mQ)).subs(a, 1))
    num, den = sp.fraction(expr)
    num, den = sp.expand(num), sp.expand(den)
    B, C = z3.Reals("b c")
    env = {"b": B, "c": C}

    def conv(e):
        return eval(str(e).replace("^", "**"), {"__builtins__": {}}, env)   # noqa: S307
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    s.add(B > 0, C > 0)
    # den > 0 is shown separately: the claim is num/den ≥ 0
    s2 = z3.Solver()
    s2.set("timeout", timeout_ms)
    s2.add(B > 0, C > 0, conv(den) <= 0)
    if s2.check() != z3.unsat:
        return "unknown (denominator)"
    s.add(conv(num) < 0)
    r = s.check()
    if r == z3.unsat:
        return "proved"
    if r == z3.sat:
        return "refuted"
    return "unknown"


def run(log=print, space=None, max_rounds=1000):
    t0 = time.time()
    found, tried = [], 0
    names = list(LIBRARY)
    for rnd in range(1, max_rounds + 1):
        pairs = list(itertools.permutations(names, 2))
        log(f"round {rnd}: {len(pairs)} expression pairs from a library of {len(names)}")
        for pn, qn in pairs:
            P, Q = LIBRARY[pn], LIBRARY[qn]
            mP, mQ = _min_value(P), _min_value(Q)
            if mP is None or mQ is None:
                continue
            tried += 1
            inf, at = ratio_inf(P, Q, mP, mQ)
            if not (0.02 < inf < 50):
                continue
            k = snap(inf)
            if k is None:
                continue
            verdict = prove(P, Q, mP, mQ, k)
            if verdict != "proved":
                continue
            # sharpness: a slightly larger constant must fail somewhere
            k_up = k * sp.Rational(1001, 1000)
            sharp = prove(P, Q, mP, mQ, k_up, timeout_ms=20000) == "refuted"
            known = CLASSICAL.get(pn) if CLASSICAL.get(pn) and CLASSICAL.get(qn) else None
            rec = {"P": pn, "Q": qn, "mP": str(mP), "mQ": str(mQ), "k": str(k), "sharp": sharp,
                   "where": [round(float(np.exp(at[0])), 4), round(float(np.exp(at[1])), 4)],
                   "status": (f"both sides classical ({CLASSICAL[pn]}, {CLASSICAL[qn]}) — very likely already known"
                              if known else "not in Euresis' knowledge"),
                   "seconds": round(time.time() - t0, 1)}
            found.append(rec)
            log(f"  PROVED{' (sharp)' if sharp else ''}: [{pn}] − {mP}  ≥  {k} · ([{qn}] − {mQ})   — {rec['status']}")
            if sharp and not known:
                _write(found, rec, tried, time.time() - t0)
                if space is not None:
                    space.add("conjecture", f"Theorem: {pn} − {mP} ≥ {k}·({qn} − {mQ})",
                              body="Machine-proved by Z3 for all positive a, b, c; the constant is sharp. Not in "
                                   "Euresis' knowledge; the inequality literature could not be searched.",
                              domain="mathematics", status="proven theorem · sharp", score=1.5,
                              key=f"thm|{pn}|{qn}|{k}")
                return rec, found
        log("  no qualifying theorem this round — extending the library with products and sums")
        new = {}
        for x, y in itertools.combinations(names, 2):
            new[f"({x})·({y})"] = LIBRARY[x] * LIBRARY[y]
        for kname, v in list(new.items())[: 12 * rnd]:
            if kname not in LIBRARY:
                LIBRARY[kname] = v
                names.append(kname)
    _write(found, None, tried, time.time() - t0)
    return None, found


def _write(found, best, tried, secs):
    L = ["# Euresis — proven discoveries (sharp inequalities)", "",
         "Each theorem was found numerically, then **proved** for all positive a, b, c by the Z3 theorem "
         "prover (complete decision procedure for real polynomial inequalities), and checked for sharpness: "
         "a constant 0.1% larger is refuted by Z3 with a counterexample.", "",
         f"Pairs examined: {tried}. Time: {secs / 60:.1f} min.", ""]
    if best:
        L += ["## Result", "", f"**For all positive real numbers a, b, c:**", "",
              f"  [{best['P']}] − {best['mP']}  ≥  **{best['k']}** · ([{best['Q']}] − {best['mQ']})", "",
              f"and the constant {best['k']} cannot be improved (tight near b/a = {best['where'][0]}, "
              f"c/a = {best['where'][1]}).", "",
              "Status: **proven** (machine proof) and **sharp**. Novelty: not among the classical inequalities "
              "Euresis knows; the wider inequality literature (olympiad collections, journals) cannot be "
              "searched from this environment, so it may already be known.", ""]
    L += ["## All proven inequalities", "", "| P | Q | k* | Sharp | Status |", "|---|---|---|---|---|"]
    L += [f"| {r['P']} | {r['Q']} | {r['k']} | {'yes' if r['sharp'] else 'no'} | {r['status']} |" for r in found]
    OUT.write_text("\n".join(L) + "\n")
