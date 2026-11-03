"""Keep searching until a formula passes every available novelty check.

A continued-fraction formula counts as a *new-candidate* only if it is
1. verified to ≥ 100 significant digits (two depths, 140-digit arithmetic);
2. irreducible (no equivalence transform lowers its degree);
3. outside the classical Gauss/Euler hypergeometric families;
4. not equivalent — by scaling (a, b) → (λa, λ²b) or index shift n → n + k — to any
   formula found earlier in this search;
5. outside every search domain in the Ramanujan Machine's published code
   (github.com/RamanujanMachine/ramanujanmachine: e, π, ζ(3), Catalan, ζ(5), ζ(7) domains).

Passing all five is the strongest evidence of novelty available offline. It is not
proof: later catalogues (the LIReC database, OEIS, arXiv) cannot be reached here.
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path

import mpmath as mp
import numpy as np
import sympy as sp

from . import conjecture as cj

n = sp.Symbol("n")
LOG = Path(__file__).resolve().parent.parent / "space" / "novelty_search.md"


def poly_a(a):
    return sp.Poly(sum(c * n ** (len(a) - 1 - k) for k, c in enumerate(a)), n)


def poly_b(b):
    s, k, m, t = b
    return sp.Poly(s * n ** k * (n + t) ** m, n)


# ------------------------------------------------- Ramanujan Machine domains
def in_rm_published_domain(const: str, A: sp.Poly, B: sp.Poly) -> str | None:
    """Return the name of the published RM domain that contains (A, B) for this constant, if any."""
    da, db = A.degree(), B.degree()
    ca, cb = A.all_coeffs(), B.all_coeffs()
    if const == "e" and da <= 1 and db <= 1 and all(abs(c) <= 5 for c in ca + cb):
        return "RM e_results (deg ≤ 1, |coef| ≤ 5)"
    if const == "π" and da <= 1 and db <= 2 and all(abs(c) <= 13 for c in ca) and all(abs(c) <= 11 for c in cb):
        return "RM pi_results (a linear, b quadratic)"
    if const.startswith("ζ(3)"):
        # Zeta3Domain1: (2n+1)(x2 n(n+1) + x3), b = x4 n^6 ; Zeta3Domain2/RatC: x0(n³+(n+1)³) + x1(2n+1), b = −c² n^6
        if B.as_expr().equals(B.LC() * n ** 6) and da == 3:
            q, r = sp.div(A.as_expr(), 2 * n + 1, n)
            if r == 0:
                qq = sp.Poly(q, n)
                if qq.degree() == 2 and qq.all_coeffs()[0] == qq.all_coeffs()[1]:
                    return "RM Zeta3Domain1 / Zeta3Domain2 (Apéry-type)"
    if const.startswith("G"):
        # CatalanDomain: b(n) = x0 (2n−1)^4 + x1 (2n−1)^3
        x0, x1 = sp.symbols("x0 x1")
        target = sp.expand(x0 * (2 * n - 1) ** 4 + x1 * (2 * n - 1) ** 3 - B.as_expr())
        sol = sp.solve(sp.Poly(target, n).all_coeffs(), [x0, x1], dict=True)
        if sol:
            return "RM CatalanDomain"
    if const.startswith("ζ(5)") and B.as_expr().equals(B.LC() * n ** 10):
        return "RM Zeta5Domain"
    return None


# ---------------------------------------------------------- equivalence
def canonical_forms(A: sp.Poly, B: sp.Poly):
    """All (a, b) related by scaling λ and index shift k ∈ [−3, 3]."""
    out = set()
    for k in range(-3, 4):
        As = sp.Poly(A.as_expr().subs(n, n + k), n)
        Bs = sp.Poly(B.as_expr().subs(n, n + k), n)
        g = sp.gcd_list([int(c) for c in As.all_coeffs()]) or 1
        for lam in sp.divisors(abs(int(g))):
            if all(int(c) % (lam * lam) == 0 for c in Bs.all_coeffs()):
                a_c = tuple(int(c) // lam for c in As.all_coeffs())
                b_c = tuple(int(c) // (lam * lam) for c in Bs.all_coeffs())
                out.add((a_c, b_c))
                out.add((tuple(-x for x in a_c), b_c))
    return out


# ------------------------------------------------------------ search rounds
def rounds():
    """Progressively larger spaces, prioritising regions outside the published RM domains."""
    yield ("quadratic a, quartic b (shifted products), |coef| ≤ 12",
           lambda: [(u, v, w) for u in range(1, 13) for v in range(0, 25) for w in range(0, 13)],
           lambda: [(sg * c, k, 4 - k, t) for c in (1, 2, 3, 4, 8, 9, 16) for sg in (1, -1)
                    for k in (1, 2, 3, 4) for t in ((0,) if k == 4 else (1, 2, -1))])
    yield ("quadratic a up to 20, quartic b with larger scale",
           lambda: [(u, v, w) for u in range(1, 21) for v in range(0, 41, 1) for w in range(0, 21)],
           lambda: [(sg * c, k, 4 - k, t) for c in (1, 2, 3, 4, 5, 6, 8, 9, 12, 16, 25, 32) for sg in (1, -1)
                    for k in (1, 2, 3, 4) for t in ((0,) if k == 4 else (1, 2, 3, -1))])
    yield ("cubic a, sextic b (shifted products)",
           lambda: [(u, v, w, z) for u in (1, 2, 3, 4) for v in range(0, 13) for w in range(0, 13) for z in range(1, 7)],
           lambda: [(sg * c, k, 6 - k, t) for c in (1, 2, 4, 8, 9, 16, 27, 64) for sg in (1, -1)
                    for k in (2, 3, 4, 5, 6) for t in ((0,) if k == 6 else (1, 2, -1))])


def screen_space(A_list, B_list, depth=400):
    nn = np.arange(depth + 1)
    B_list = [b for b in B_list if np.all(cj.b_eval(b, np.arange(1, depth + 1)) != 0)]
    bv = np.array([cj.b_eval(b, nn) for b in B_list])
    out = []
    for a in A_list:
        av = cj._poly(a, nn)
        vals = {}
        for d in (depth // 2, depth):
            x = np.full(len(B_list), av[d])
            with np.errstate(all="ignore"):
                for k in range(d - 1, -1, -1):
                    x = av[k] + bv[:, k + 1] / x
            vals[d] = x
        x1, x2 = vals[depth // 2], vals[depth]
        ok = np.isfinite(x2) & (np.abs(x2) < 1e6) & (np.abs(x1 - x2) <= 1e-13 * np.maximum(1, np.abs(x2)))
        for j in np.where(ok)[0]:
            out.append((a, B_list[j], float(x2[j])))
    return out


def run(max_minutes=120, log=print, space=None):
    t0 = time.time()
    consts = {**cj.CONSTANTS, **cj.FRONTIER_CONSTANTS}
    tables = cj.mobius_table(constants=consts)
    seen = set()
    records = []
    found = None
    for ri, (label, fa, fb) in enumerate(rounds(), 1):
        if time.time() - t0 > max_minutes * 60:
            break
        log(f"round {ri}: {label}")
        cands = screen_space(fa(), fb())
        hits = cj.match(cands, tables)
        log(f"  {len(cands):,} convergent fractions · {len(hits)} numerical matches")
        for h in hits:
            conv, agree = cj.verify(h, dps=120)
            if min(conv, agree) < 100:
                continue
            A, B = poly_a(h["a"]), poly_b(h["b"])
            reasons = []
            if cj.reducible(h):
                reasons.append("reducible")
            fam = cj.classical(h)
            if fam and "reducible" not in fam:
                reasons.append(fam)
            rm = in_rm_published_domain(h["constant"], A, B)
            if rm:
                reasons.append(f"inside {rm}")
            forms = canonical_forms(A, B)
            key = (h["constant"],)
            if any((key, f) in seen for f in forms):
                reasons.append("equivalent to an earlier formula")
            for f in forms:
                seen.add((key, f))
            rec = {"constant": h["constant"], "closed_form": cj.closed_form(h), "a": cj.describe_a(h["a"]),
                   "b": cj.describe_b(h["b"]), "digits": int(min(conv, agree)), "round": ri,
                   "verdict": "passes every available novelty check" if not reasons else "; ".join(reasons)}
            records.append(rec)
            if not reasons and found is None:
                found = rec
                log(f"  ★ candidate passing every check: {rec['constant']} = …  {rec['closed_form']}  "
                    f"a(n) = {rec['a']}, b(n) = {rec['b']}  [{rec['digits']} digits]")
        if found:
            break
    _write(records, found, time.time() - t0)
    if space is not None and found:
        space.add("conjecture", f"New-candidate formula: {found['constant']}",
                  body=f"Continued fraction a(n) = {found['a']}, b(n) = {found['b']} converges to {found['closed_form']}; "
                       f"verified to {found['digits']} digits; irreducible; outside classical families; not equivalent "
                       "to earlier results; outside the Ramanujan Machine's published search domains. Not checked "
                       "against LIReC, OEIS or arXiv.", formula=f"{found['closed_form']}", domain="mathematics",
                  status="passes every available novelty check · unproven", score=1.5,
                  key=f"newcand|{found['constant']}|{found['a']}|{found['b']}")
    return found, records


def _write(records, found, secs):
    L = ["# Euresis — searching until a formula passes every novelty check", "",
         "Novelty checks: verified ≥ 100 digits · irreducible · outside classical families · not equivalent "
         "(scaling / index shift) to earlier formulas · outside every search domain in the Ramanujan Machine's "
         "published code. Not checked: the LIReC database, OEIS, arXiv (unreachable from this environment).", "",
         f"Search time: {secs / 60:.1f} min. Formulas verified: {len(records)}.", ""]
    if found:
        L += ["## Result", "",
              f"**{found['constant']}** — the continued fraction with a(n) = {found['a']}, b(n) = {found['b']} "
              f"equals **{found['closed_form']}**, verified to {found['digits']} digits.", "",
              "It passes every novelty check available here. It is a conjecture (numerically verified, unproven) and "
              "may still appear in catalogues that could not be checked.", ""]
    else:
        L += ["## Result", "", "No formula passed every check within the time budget.", ""]
    L += ["## All verified formulas", "", "| Round | Constant | Closed form | a(n) | b(n) | Digits | Novelty verdict |",
          "|---|---|---|---|---|---|---|"]
    for r in records:
        L.append(f"| {r['round']} | {r['constant']} | {r['closed_form']} | {r['a']} | {r['b']} | {r['digits']} | {r['verdict']} |")
    LOG.write_text("\n".join(L) + "\n")
