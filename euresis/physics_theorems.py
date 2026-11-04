"""Proven theorems about physical laws.

Euresis looks through its knowledge base for pairs of laws that predict the
*same* quantity from the *same* inputs (e.g. a classical and a relativistic
formula, or two models of one effect). Through dimensional analysis both become
functions of the same dimensionless groups. For each pair it

1. discovers the sharp bounds of the ratio  R = law₁ / law₂  over every
   physically allowed value (all inputs positive, square roots real);
2. **proves** the bound with the Z3 theorem prover — square roots are handled
   exactly by introducing s with s² = argument, s ≥ 0;
3. checks sharpness (a bound 0.1 % tighter is refuted);
4. reports whether the statement is already in Euresis' knowledge.

A theorem proven this way is certain *for the laws as stated*; whether nature
obeys those laws is a matter for experiment, not proof.
"""
from __future__ import annotations

import itertools
import re
from fractions import Fraction
from pathlib import Path

import numpy as np
import sympy as sp
from scipy.optimize import minimize

from .engine import Engine, _as_relation
from .kb import KnowledgeBase, family

OUT = Path(__file__).resolve().parent.parent / "space" / "physics_theorems.md"


def candidate_pairs(kb: KnowledgeBase, E: Engine):
    """Laws with the same target family and the same input families."""
    entries = []
    for f in kb.formulas:
        if not isinstance(f.eq.lhs, sp.Symbol) or f.eq.lhs not in f.sym_to_q:
            continue
        t = f.eq.lhs
        sols = E.solve_for(_as_relation(f), t)
        if not sols:
            continue
        ins = {s: q for s, q in f.sym_to_q.items() if s != t}
        if not ins or len(ins) > 3:
            continue
        fams = [family(q) for q in ins.values()]
        if len(set(fams)) != len(fams):        # e.g. R1, R2 — merging them would silently assume they are equal
            continue
        key = (family(f.sym_to_q[t]), frozenset(family(q) for q in ins.values()))
        entries.append((key, f, t, sols[0], ins))
    by_key = {}
    for e in entries:
        by_key.setdefault(e[0], []).append(e)
    pairs = []
    for key, es in by_key.items():
        for x, y in itertools.combinations(es, 2):
            if x[1].name != y[1].name:
                pairs.append((x, y))
    return pairs


def unify(x, y):
    """Express both right-hand sides in the same input symbols (matched by family)."""
    fam_sym = {}
    for s, q in x[4].items():
        fam_sym[family(q)] = sp.Symbol(family(q), positive=True)
    sub_x = {s: fam_sym[family(q)] for s, q in x[4].items()}
    sub_y = {s: fam_sym[family(q)] for s, q in y[4].items()}
    consts = {sp.Symbol(k): sp.Symbol(k, positive=True) for k in ("c", "G", "h", "hbar", "k_B", "e", "epsilon_0", "mu_0")}
    return x[3].subs(consts).subs(sub_x), y[3].subs(consts).subs(sub_y), list(fam_sym.values())


def _bounds(R, syms, starts=80, seed=0):
    f = sp.lambdify(syms, R, "numpy")
    rng = np.random.default_rng(seed)
    lo, hi = np.inf, -np.inf

    def val(z):
        with np.errstate(all="ignore"):
            v = complex(f(*np.exp(z)))
        return v.real if abs(v.imag) < 1e-12 and np.isfinite(v.real) else None
    for _ in range(starts):
        z0 = rng.uniform(-6, 6, len(syms))
        for sgn in (1, -1):
            r = minimize(lambda z: (sgn * val(z)) if val(z) is not None else 1e9, z0, method="Nelder-Mead",
                         options={"xatol": 1e-11, "fatol": 1e-13, "maxiter": 4000})
            v = val(r.x)
            if v is None:
                continue
            lo, hi = (min(lo, v), hi) if sgn == 1 else (lo, max(hi, v))
    return lo, hi


def _snap(x):
    if not np.isfinite(x):
        return None
    fr = Fraction(x).limit_denominator(48)
    return sp.Rational(fr.numerator, fr.denominator) if abs(float(fr) - x) < 1e-6 * max(1, abs(x)) else None


def z3_prove(claim, syms, assumptions=()):
    """Prove claim (a sympy relational with sqrt allowed) for all positive symbols with real square roots,
    within the domain given by `assumptions` (sympy relationals, e.g. beta < 1)."""
    import z3
    env, cons, counter = {}, [], itertools.count()
    syms = sorted(set(syms) | getattr(claim, "free_symbols", set())
                  | set().union(*[getattr(x, "free_symbols", set()) for x in assumptions]), key=str)
    zs = {s: z3.Real(str(s)) for s in syms}
    cons += [v > 0 for v in zs.values()]

    def conv(e):
        if e.is_Symbol:
            return zs[e]
        if e.is_Number:
            return z3.RealVal(str(sp.Rational(e)))
        if e.is_Add:
            return sum((conv(t) for t in e.args[1:]), conv(e.args[0]))
        if e.is_Mul:
            out = conv(e.args[0])
            for t in e.args[1:]:
                out = out * conv(t)
            return out
        if e.is_Pow:
            base, ex = e.args
            ex = sp.Rational(ex)
            if ex.q == 2:                                       # square root: s² = base, s ≥ 0
                s = z3.Real(f"s{next(counter)}")
                bz = conv(base)
                cons.extend([s >= 0, s * s == bz, bz >= 0])
                if ex < 0:                                      # in a denominator: only where it is defined
                    cons.append(s > 0)
                r = s
                p = abs(ex.p)
                out = r
                for _ in range(p - 1):
                    out = out * r
                return out if ex > 0 else 1 / out
            if ex.q == 1:
                bz = conv(base)
                if ex < 0:                                      # 1/x is asserted only where x ≠ 0
                    cons.append(bz != 0)
                out = bz
                for _ in range(abs(ex.p) - 1):
                    out = out * bz
                return out if ex > 0 else 1 / out
        raise ValueError(f"unsupported: {e}")
    if claim is sp.true:                       # SymPy already decided it identically
        return "proved"
    if claim is sp.false:
        return "refuted"
    if not isinstance(claim, sp.core.relational.Relational):
        return "unsupported"
    lhs, rhs = claim.lhs, claim.rhs
    s = z3.Solver()
    s.set("timeout", 60000)
    ops = {sp.GreaterThan: lambda a, b: a >= b, sp.StrictGreaterThan: lambda a, b: a > b,
           sp.LessThan: lambda a, b: a <= b, sp.StrictLessThan: lambda a, b: a < b,
           sp.Equality: lambda a, b: a == b}
    op = next((f for cls, f in ops.items() if isinstance(claim, cls)), None)
    if op is None:
        return "unsupported"
    try:
        goal = op(conv(lhs), conv(rhs))
        for asm in assumptions:                 # the physical domain
            aop = next((f for cls, f in ops.items() if isinstance(asm, cls)), None)
            if aop is None:
                return "unsupported"
            cons.append(aop(conv(asm.lhs), conv(asm.rhs)))
    except (ValueError, TypeError):
        return "unsupported"
    s.add(*cons)
    s.add(z3.Not(goal))
    r = s.check()
    return "proved" if r == z3.unsat else ("refuted" if r == z3.sat else "unknown")


KNOWN = {("Kinetic energy", "Relativistic kinetic energy"): "relativistic kinetic energy exceeds the classical value",
         ("Escape velocity", "Circular orbital velocity"): "escape speed is √2 × circular speed"}


def run(log=print, space=None):
    kb = KnowledgeBase()
    E = Engine(kb)
    pairs = candidate_pairs(kb, E)
    log(f"{len(pairs)} pairs of laws predict the same quantity from the same inputs")
    results = []
    for x, y in pairs:
        try:
            fx, fy, syms = unify(x, y)
        except Exception:
            continue
        R = sp.simplify(fx / fy)
        if R.has(sp.zoo, sp.oo, sp.nan) or R == 0 or fx == 0 or fy == 0:
            continue                              # degenerate pair (a law with no content for this target)
        if not R.free_symbols:
            results.append({"A": x[1].name, "B": y[1].name, "kind": "constant ratio", "statement": f"{x[1].name} = {R} × {y[1].name}",
                            "proved": "exact (algebra)", "known": KNOWN.get((x[1].name, y[1].name)) or KNOWN.get((y[1].name, x[1].name))})
            continue
        rsyms = sorted(R.free_symbols, key=str)
        lo, hi = _bounds(R, rsyms)
        for kind, v in (("lower", lo), ("upper", hi)):
            k = _snap(v)
            if k is None or k == 0:
                continue
            claim = sp.Ge(fx, k * fy) if kind == "lower" else sp.Ge(k * fy, fx)
            verdict = z3_prove(claim, rsyms)
            if verdict != "proved":
                continue
            tighter = sp.Ge(fx, k * sp.Rational(1001, 1000) * fy) if kind == "lower" else sp.Ge(k * sp.Rational(999, 1000) * fy, fx)
            sharp = z3_prove(tighter, rsyms) == "refuted"
            stmt = (f"{x[1].name} ≥ {k} × {y[1].name}" if kind == "lower" else f"{x[1].name} ≤ {k} × {y[1].name}")
            known = KNOWN.get((x[1].name, y[1].name)) or KNOWN.get((y[1].name, x[1].name))
            results.append({"A": x[1].name, "B": y[1].name, "kind": f"{kind} bound", "statement": stmt,
                            "proved": "Z3 proof", "sharp": sharp, "known": known})
            log(f"  PROVED{' (sharp)' if sharp else ''}: {stmt}" + (f"   [known: {known}]" if known else ""))
    L = ["# Euresis — proven theorems about physical laws", "",
         "Pairs of laws in Euresis' knowledge that predict the same quantity from the same inputs. Bounds were "
         "discovered numerically and proved for every physically allowed value by the Z3 theorem prover. "
         "Proven means certain *for the laws as stated*; whether nature follows them is for experiment.", "",
         "| Statement | Proof | Sharp | Already known? |", "|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['statement']} | {r['proved']} | {'yes' if r.get('sharp') else ('—' if r['kind'] == 'constant ratio' else 'no')} | "
                 f"{r['known'] or 'not in Euresis’ knowledge'} |")
    OUT.write_text("\n".join(L) + "\n")
    if space is not None:
        for r in results:
            if r["proved"] == "Z3 proof":
                space.add("conjecture", f"Theorem: {r['statement']}", body="Proved by Z3 for all physically allowed values.",
                          domain="physics", status="proven theorem", score=1.2, key=f"phys|{r['statement']}")
    return results
