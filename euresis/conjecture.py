"""Mathematical discovery: new formulas for fundamental constants.

Euresis searches polynomial continued fractions

    L = a(0) + b(1) / (a(1) + b(2) / (a(2) + b(3) / (a(3) + …)))

with a(n), b(n) small integer polynomials, and asks whether each limit L equals a
Möbius transform (p + q·c)/(r + s·c) of a fundamental constant c (π, e, ζ(3),
Catalan's G, ln 2, ln 3, √2, √3, Euler's γ, π², ζ(5)). The method follows the
Ramanujan Machine (Raayoni et al., Nature 590, 67–73, 2021).

Pipeline
1. **Fast screen** — every continued fraction is evaluated in double precision
   (vectorised); divergent or slowly converging ones are discarded.
2. **Match** — the value is looked up against all Möbius transforms of every
   constant with integer coefficients |p|,|q|,|r|,|s| ≤ 8 (relative tolerance 1e-11).
3. **Verify** — each match is recomputed with 120-digit arithmetic at two depths;
   it is kept only if the continued fraction and the closed form agree to ≥ 60 digits.
4. **Classify** — matches equal to classical formulas Euresis knows are marked
   *known*; the rest are *conjectures*: verified numerically to many digits,
   unproven, and not checked against published catalogues from this environment.
"""
from __future__ import annotations

import itertools
import math
from fractions import Fraction
from pathlib import Path

import mpmath as mp
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "space" / "conjectures.md"

FRONTIER_CONSTANTS = {
    "π³": lambda: mp.pi ** 3, "π·ln 2": lambda: mp.pi * mp.log(2), "ln² 2": lambda: mp.log(2) ** 2,
    "G/π": lambda: mp.catalan / mp.pi, "ζ(3)/π²": lambda: mp.zeta(3) / mp.pi ** 2, "π⁴": lambda: mp.pi ** 4,
    "ζ(3)·π": lambda: mp.zeta(3) * mp.pi,
}

CONSTANTS = {
    "π": lambda: mp.pi, "e": lambda: mp.e, "ζ(3)": lambda: mp.zeta(3), "G (Catalan)": lambda: mp.catalan,
    "ln 2": lambda: mp.log(2), "ln 3": lambda: mp.log(3), "√2": lambda: mp.sqrt(2), "√3": lambda: mp.sqrt(3),
    "γ (Euler)": lambda: mp.euler, "π²": lambda: mp.pi ** 2, "ζ(5)": lambda: mp.zeta(5),
}

# classical continued fractions Euresis already knows (a(n) coefficients high→low, b(n) as a lambda description)
KNOWN = [
    ("e (Euler)", lambda a, b: a == (1, 1) and b == ("n", 1, 1, 0)),
]


def _poly(c, n):
    out = np.zeros_like(n, dtype=float)
    for k in c:
        out = out * n + k
    return out


def a_family():
    for u in range(1, 7):
        for v in range(0, 7):
            yield (u, v)                        # a(n) = u n + v
    for u in range(1, 4):
        for v in range(0, 5):
            for w in range(0, 4):
                yield (u, v, w)                 # a(n) = u n² + v n + w
    for al in range(1, 41):
        for be in range(1, 13):
            yield (2 * al, 3 * al, al + 2 * be, be)   # a(n) = (2n+1)(αn² + αn + β): Apéry-type cubic
    for u in (1, 2):
        for v in range(0, 5):
            for w in range(0, 5):
                for z in range(1, 4):
                    yield (u, v, w, z)          # generic small cubic


def b_family():
    for s in (1, -1, 2, -2, 4, -4):
        for k in (1, 2, 3, 4, 5, 6):
            for m in (0, 1, 2, 3):
                for t in (-1, 0, 1, 2):
                    if m == 0 and t != 0:
                        continue
                    yield (s, k, m, t)          # b(n) = s · n^k · (n + t)^m


def b_eval(spec, n):
    s, k, m, t = spec
    return s * n.astype(float) ** k * (n + t).astype(float) ** m


def describe_a(a):
    if len(a) == 2:
        return f"{a[0]}n + {a[1]}"
    if len(a) == 3:
        return f"{a[0]}n² + {a[1]}n + {a[2]}"
    return f"{a[0]}n³ + {a[1]}n² + {a[2]}n + {a[3]}"


def reducible(h) -> bool:
    """A continued fraction is equivalent to a lower-degree one if some g(n) = n + t divides a(n) and
    g(n−1)·g(n) divides b(n): the equivalence transform c_n = 1/g(n) then lowers both degrees."""
    import sympy as sp
    n = sp.Symbol("n")
    a = sp.Poly(sum(c * n ** (len(h["a"]) - 1 - k) for k, c in enumerate(h["a"])), n)
    sg, k, m, t = h["b"]
    b = sp.Poly(sg * n ** k * (n + t) ** m, n)
    for root in range(-6, 7):
        g = sp.Poly(n - root, n)
        if a.rem(g).is_zero and b.rem(g * sp.Poly(n - 1 - root, n)).is_zero:
            return True
    return False


def classical(h) -> str | None:
    """Families mapped out long ago: degree(a) ≤ 1 with degree(b) ≤ 2 are Gauss/Euler hypergeometric
    continued fractions; Apéry's ζ(3) and Brouncker's π are named."""
    a, b = h["a"], h["b"]
    if a == (34, 51, 27, 5) and b == (-1, 6, 0, 0):
        return "Apéry (1979)"
    if a == (2, 1) and b == (1, 1, 1, 0):
        return "Brouncker (1655)"
    if reducible(h):
        return "reducible to a lower-degree (classical) continued fraction"
    if len(a) <= 2 and b[1] + b[2] <= 2:
        return "Gauss/Euler hypergeometric family — almost certainly known"
    if len(a) == 3 and b[1] + b[2] <= 3:
        return "low-degree family — likely known"
    return None


def describe_b(b):
    s, k, m, t = b
    core = f"n^{k}" if k > 1 else "n"
    if m:
        tt = f"(n {'+' if t >= 0 else '−'} {abs(t)})" if t else "n"
        core += f"·{tt}^{m}" if m > 1 else f"·{tt}"
    return f"{s}·{core}" if s != 1 else core


def frontier_a():
    """Beyond the published families: scaled Apéry-type cubics and ζ(5)-oriented quintics."""
    for al in range(1, 61):
        for be in range(1, 31):
            yield (2 * al, 3 * al, al + 2 * be, be)                 # (2n+1)(α n(n+1) + β)
    for u in range(1, 21):
        for v in range(0, 41):
            for w in range(1, 11):
                # (2n+1)(u m² + v m + w), m = n(n+1)  → degree-5 polynomial, coefficients high→low
                yield (2 * u, 5 * u, 4 * u + 2 * v, u + 3 * v, v + 2 * w, w)


def sweep_a():
    for u in range(1, 13):
        for v in range(0, 25):
            for w in range(0, 13):
                yield (u, v, w)


def sweep_b():
    for c in (1, 2, 3, 4, 8, 9, 16):
        for sg in (1, -1):
            yield (sg * c, 4, 0, 0)
            for t in (1, 2, -1):
                yield (sg * c, 3, 1, t)
                yield (sg * c, 2, 2, t)
                yield (sg * c, 1, 3, t)


def frontier_b():
    for c in (1, 2, 4, 8, 9, 16, 27, 32, 64):
        yield (-c, 6, 0, 0)
        yield (-c, 10, 0, 0)
        yield (-c, 5, 1, 1)
        yield (-c, 3, 3, 1)


def screen(depth=400, frontier=False):
    """Evaluate every continued fraction in double precision; keep convergent, irrational-looking ones."""
    n = np.arange(depth + 1)
    fa = {False: a_family, True: frontier_a, "sweep": sweep_a}[frontier]
    fb = {False: b_family, True: frontier_b, "sweep": sweep_b}[frontier]
    A = list(fa())
    B = [b for b in fb() if np.all(b_eval(b, np.arange(1, depth + 1)) != 0)]
    av = np.array([_poly(a, n) for a in A])               # (nA, depth+1)
    bv = np.array([b_eval(b, n) for b in B])              # (nB, depth+1)
    out = []
    for i, a in enumerate(A):
        vals = {}
        for d in (depth // 2, depth):
            x = np.full(len(B), av[i, d])
            with np.errstate(all="ignore"):
                for k in range(d - 1, -1, -1):
                    x = av[i, k] + bv[:, k + 1] / x
            vals[d] = x
        x1, x2 = vals[depth // 2], vals[depth]
        ok = np.isfinite(x2) & (np.abs(x2) < 1e6) & (np.abs(x1 - x2) <= 1e-13 * np.maximum(1, np.abs(x2)))
        for j in np.where(ok)[0]:
            out.append((a, B[j], float(x2[j])))
    return out


def mobius_table(limit=8, constants=None):
    """All values (p + q c)/(r + s c) for each constant, with q·r − p·s ≠ 0 (genuinely involves c)."""
    mp.mp.dps = 30
    tables = {}
    rng = range(-limit, limit + 1)
    for name, f in (constants or CONSTANTS).items():
        c = float(f())
        vals, keys = [], []
        for p, q, r, s in itertools.product(rng, rng, rng, rng):
            if q * r - p * s == 0 or (r == 0 and s == 0):
                continue
            if math.gcd(math.gcd(abs(p), abs(q)), math.gcd(abs(r), abs(s))) != 1:
                continue
            den = r + s * c
            if abs(den) < 1e-9:
                continue
            vals.append((p + q * c) / den)
            keys.append((p, q, r, s))
        order = np.argsort(vals)
        tables[name] = (np.array(vals)[order], [keys[k] for k in order])
    return tables


def _rational(x, maxden=1000):
    fr = Fraction(x).limit_denominator(maxden)
    return abs(float(fr) - x) < 1e-11 * max(1, abs(x))


def match(cands, tables, tol=1e-11):
    hits = []
    for a, b, x in cands:
        if _rational(x):
            continue
        for name, (vals, keys) in tables.items():
            i = np.searchsorted(vals, x)
            for j in (i - 1, i):
                if 0 <= j < len(vals) and abs(vals[j] - x) <= tol * max(1, abs(x)):
                    hits.append({"a": a, "b": b, "value": x, "constant": name, "mobius": keys[j]})
    return hits


def cf_mp(a, b, depth):
    x = mp.mpf(0)
    n = depth
    x = mp.mpf(sum(c * n ** (len(a) - 1 - k) for k, c in enumerate(a)))
    for n in range(depth - 1, -1, -1):
        an = sum(c * n ** (len(a) - 1 - k) for k, c in enumerate(a))
        s, k, m, t = b
        bn1 = s * (n + 1) ** k * (n + 1 + t) ** m
        x = an + mp.mpf(bn1) / x
    return x


def verify(hit, dps=120):
    mp.mp.dps = dps + 20
    v1 = cf_mp(hit["a"], hit["b"], 1500)
    v2 = cf_mp(hit["a"], hit["b"], 3000)
    c = {**CONSTANTS, **FRONTIER_CONSTANTS}[hit["constant"]]()
    p, q, r, s = hit["mobius"]
    closed = (p + q * c) / (r + s * c)
    conv = -mp.log10(abs(v2 - v1) / abs(v2)) if v2 != v1 else dps
    agree = -mp.log10(abs(v2 - closed) / abs(closed)) if v2 != closed else dps
    return float(min(conv, dps)), float(min(agree, dps))


def closed_form(hit):
    p, q, r, s = hit["mobius"]
    c = hit["constant"]
    num = " + ".join(t for t in [f"{p}" if p else "", f"{q}·{c}" if q else ""] if t) or "0"
    den = " + ".join(t for t in [f"{r}" if r else "", f"{s}·{c}" if s else ""] if t) or "1"
    return f"({num}) / ({den})".replace("+ -", "− ").replace("1·", "")


def run(log=print, space=None, frontier=False):
    log("1. screening continued fractions (double precision)…")
    cands = screen(frontier=frontier)
    log(f"   {len(cands)} convergent continued fractions")
    consts = {**CONSTANTS, **FRONTIER_CONSTANTS} if frontier else CONSTANTS
    log(f"2. building Möbius tables for {len(consts)} constants…")
    tables = mobius_table(constants=consts)
    hits = match(cands, tables)
    log(f"   {len(hits)} numerical matches")
    log("3. verifying each match with 120-digit arithmetic…")
    verified = []
    for h in hits:
        conv, agree = verify(h)
        h["digits_converged"], h["digits_agree"] = round(conv), round(agree)
        if agree >= 60 and conv >= 60:
            h["known"] = classical(h)
            verified.append(h)
    # group by (constant, closed form) — the same constant can be reached by many fractions
    groups, seen = {}, {}
    for h in verified:
        key = (h["constant"], round(h["value"], 10))
        if key in seen:
            groups[seen[key]].append(h)
            continue
        g = (h["constant"], closed_form(h))
        seen[key] = g
        groups.setdefault(g, []).append(h)
    log(f"   {len(verified)} verified to ≥ 60 digits; {len(groups)} distinct closed forms")
    new = [g for g, hs in groups.items() if not any(h.get("known") for h in hs)]
    log(f"   {len(new)} outside the classical families (candidate new formulas):")
    for g in new:
        h = groups[g][0]
        log(f"     {g[0]}: {g[1]}   a(n) = {describe_a(h['a'])}, b(n) = {describe_b(h['b'])}  [{h['digits_agree']} digits]")
    L = ["# Euresis — mathematical conjectures", "",
         "Euresis searched polynomial continued fractions (Ramanujan-Machine style) and matched their limits "
         "against fundamental constants. Every entry below was **verified to at least 60 significant digits** "
         "(120-digit arithmetic, two depths). These are *conjectures*: numerically certain to that precision, "
         "unproven, and **not checked against published catalogues** (the Ramanujan Machine database, OEIS, "
         "arXiv) because this environment cannot reach them. Many low-complexity fractions are likely already "
         "known.", "",
         f"Searched: {len(cands)} convergent continued fractions · 11 constants · Möbius coefficients up to 8.", "",
         "| Constant | Closed form of the limit | a(n) | b(n) | Digits verified |", "|---|---|---|---|---|"]
    for (cname, cf), hs in sorted(groups.items(), key=lambda kv: (kv[0][0], -len(kv[1]))):
        h = min(hs, key=lambda x: (len(x["a"]), abs(x["b"][0]), x["b"][1] + x["b"][2]))
        tag = f" — *{h['known']}*" if h.get("known") else " — **not a classical family: candidate new formula**"
        L.append(f"| {cname} | {cf}{tag} | {describe_a(h['a'])} | {describe_b(h['b'])} | {h['digits_agree']} |")
    out = {False: OUT, True: OUT.with_name("conjectures_frontier.md"), "sweep": OUT.with_name("conjectures_sweep.md")}[frontier]
    out.write_text("\n".join(L) + "\n")
    if space is not None:
        for (cname, cf), hs in groups.items():
            h = hs[0]
            space.add("conjecture", f"{cname}: continued fraction = {cf}",
                      body=f"a(n) = {describe_a(h['a'])}, b(n) = {describe_b(h['b'])}. Verified to "
                           f"{h['digits_agree']} digits. Unproven; novelty not checked against published catalogues.",
                      formula=f"{describe_a(h['a'])} ; {describe_b(h['b'])} → {cf}", domain="mathematics",
                      status="conjecture · numerically verified", score=1.0, key=f"conj|{cname}|{cf}")
    log(f"report: {out.relative_to(out.parents[1])}")
    return groups, len(cands)
