"""Physics-informed symbolic regression: recover exact equations from data.

Pipeline (in the spirit of AI Feynman, Udrescu & Tegmark 2020):

1. **Dimensional reduction.** With the SI dimensions of every input and of the
   target, Buckingham's Π theorem rewrites  y = f(x₁…x_k)  as
   y = M(x)·F(π₁…π_m), where M is a monomial carrying y's units and the π are
   the m dimensionless groups (m = k − rank). Most laws collapse to 0–2 groups.
2. **Form search.** F is fitted with a library of functional families — power
   laws, shifted/saturating powers, exponentials, Boltzmann/Planck forms,
   trigonometric, logarithmic, rational (Michaelis–Menten/Hill) and sums of
   power terms — each with its constants found by nonlinear least squares from
   many starting points.
3. **Snapping.** Exponents are snapped to simple rationals and coefficients
   to closed forms (π, √2, …); a snapped model is kept only if it still fits
   to machine precision. The result is an exact symbolic equation.
4. **Selection.** Validation error on held-out rows decides; among exact fits
   the simplest wins.
"""
from __future__ import annotations

import itertools
import math
import warnings
from dataclasses import dataclass

import numpy as np
import sympy as sp
from scipy.optimize import least_squares

from .dimensions import Dim

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ------------------------------------------------------------ Π analysis
def pi_analysis(dims: list[Dim], target: Dim):
    """Return (monomial exponents for the target's units, list of integer Π exponent vectors) or None."""
    A = sp.Matrix([[d[i] for d in dims] for i in range(7)])
    b = sp.Matrix([target[i] for i in range(7)])
    null = []
    for v in A.nullspace():
        dens = [int(sp.fraction(x)[1]) for x in v]
        den = dens[0] if len(dens) == 1 else sp.ilcm(*dens)
        v = v * den
        nz = [abs(int(x)) for x in v if x != 0]
        g = nz[0] if len(nz) == 1 else sp.igcd(*nz)
        v = v / g
        if sum(1 for x in v if x < 0) > sum(1 for x in v if x > 0):
            v = -v
        null.append([int(x) for x in v])
    null = _sparsify(null)
    try:
        sol, params = A.gauss_jordan_solve(b)
    except ValueError:
        return None
    base = sol.subs({p: 0 for p in params}) if params.shape[0] else sol
    base = [sp.Rational(x) for x in base]
    # choose the particular solution that is sparsest / smallest
    best = None
    rng = range(-2, 3)
    for ks in itertools.product(rng, repeat=min(len(null), 3)):
        e = [base[i] + sum(k * null[j][i] for j, k in enumerate(ks)) for i in range(len(dims))]
        cost = (sum(1 for x in e if x != 0), sum(abs(x) for x in e), sum(1 for x in e if x < 0))
        if best is None or cost < best[0]:
            best = (cost, e)
    return best[1], null


def _sparsify(null):
    """Make Π groups as simple as possible by combining basis vectors."""
    null = [list(v) for v in null]
    changed = True
    while changed:
        changed = False
        for i, j in itertools.permutations(range(len(null)), 2):
            for k in (-2, -1, 1, 2):
                w = [a + k * b for a, b in zip(null[i], null[j])]
                if any(w) and (sum(1 for x in w if x) < sum(1 for x in null[i] if x) or
                               (sum(1 for x in w if x) == sum(1 for x in null[i] if x)
                                and sum(map(abs, w)) < sum(map(abs, null[i])))):
                    null[i] = w
                    changed = True
    return null


# -------------------------------------------------------------- families
@dataclass
class Family:
    name: str
    n_params: int
    f: callable              # f(P, *params) with P the (n, m) Π matrix
    expr: callable           # expr(pis, params) -> sympy expression
    inits: list              # list of parameter starting vectors
    needs: int = 1           # minimum number of Π groups
    special: bool = True     # uses one distinguished Π (others enter as power factors)


def _pw(x, p):
    return np.power(x, p)


def families() -> list[Family]:
    E = [-2, -1, -0.5, 0.5, 1, 2, 3, 4]
    F = [
        Family("a·x^p", 2, lambda x, a, p: a * _pw(x, p), lambda x, a, p: a * x ** p,
               [[1, e] for e in E]),
        Family("a + b·x^p", 3, lambda x, a, b, p: a + b * _pw(x, p), lambda x, a, b, p: a + b * x ** p,
               [[1, s, e] for e in E for s in (1, -1)]),
        Family("(a + b·x^p)^q", 4, lambda x, a, b, p, q: _pw(a + b * _pw(x, p), q),
               lambda x, a, b, p, q: (a + b * x ** p) ** q,
               [[1, s, e, q] for e in (1, 2, -1, -2) for s in (1, -1) for q in (0.5, -0.5, 2, -1)]),
        Family("a·exp(b·x^p)", 3, lambda x, a, b, p: a * np.exp(b * _pw(x, p)),
               lambda x, a, b, p: a * sp.exp(b * x ** p), [[1, s, e] for e in (1, -1, 2) for s in (1, -1)]),
        Family("a/(exp(b·x^p) + c)", 4, lambda x, a, b, p, c: a / (np.exp(b * _pw(x, p)) + c),
               lambda x, a, b, p, c: a / (sp.exp(b * x ** p) + c), [[1, 1, e, -1] for e in (1, -1)] +
               [[1, 1, e, 1] for e in (1, -1)]),
        Family("a·x^p·exp(b·x^r)", 4, lambda x, a, p, b, r: a * _pw(x, p) * np.exp(b * _pw(x, r)),
               lambda x, a, p, b, r: a * x ** p * sp.exp(b * x ** r),
               [[1, p, -1, r] for p in (1, 2, -1) for r in (1, -1)]),
        Family("a·x^p/(exp(b·x^r) + c)", 5,
               lambda x, a, p, b, r, c: a * _pw(x, p) / (np.exp(b * _pw(x, r)) + c),
               lambda x, a, p, b, r, c: a * x ** p / (sp.exp(b * x ** r) + c),
               [[1, p, 1, r, -1] for p in (-5, -3, 3, 5, -2, 2) for r in (-1, 1)]),
        Family("a·sin(b·x)", 2, lambda x, a, b: a * np.sin(b * x), lambda x, a, b: a * sp.sin(b * x),
               [[1, 1], [1, 2]]),
        Family("a·cos(b·x)^p", 3, lambda x, a, b, p: a * _pw(np.cos(b * x), p),
               lambda x, a, b, p: a * sp.cos(b * x) ** p, [[1, 1, 1], [1, 1, 2]]),
        Family("a·sin(x)^p", 2, lambda x, a, p: a * _pw(np.sin(x), p), lambda x, a, p: a * sp.sin(x) ** p,
               [[1, 1], [1, 2], [1, -1]]),
        Family("a + b·log(x)", 2, lambda x, a, b: a + b * np.log(x), lambda x, a, b: a + b * sp.log(x),
               [[0, 1], [1, -1]]),
        Family("a·log(1 + b·x)", 2, lambda x, a, b: a * np.log1p(b * x), lambda x, a, b: a * sp.log(1 + b * x),
               [[1, 1]]),
        Family("a·x^p/(b + x^p)", 3, lambda x, a, b, p: a * _pw(x, p) / (b + _pw(x, p)),
               lambda x, a, b, p: a * x ** p / (b + x ** p), [[1, 1, p] for p in (1, 2, 4)]),
        Family("a·x^p/(1 + b·x)", 3, lambda x, a, b, p: a * _pw(x, p) / (1 + b * x),
               lambda x, a, b, p: a * x ** p / (1 + b * x), [[1, 1, 1], [1, 1, 2]]),
        Family("a·x·(1 − x/b)", 2, lambda x, a, b: a * x * (1 - x / b), lambda x, a, b: a * x * (1 - x / b),
               [[1, 10]]),
    ]
    return F


# ------------------------------------------------------------------ fit
@dataclass
class Fit:
    family: str
    special: int | None
    params: np.ndarray
    others: np.ndarray       # power exponents of non-special Π groups
    val_err: float
    n_params: int
    snapped: bool = False
    expr_F: sp.Expr | None = None


def _rel_resid(pred, y):
    r = (pred - y) / np.maximum(np.abs(y), 1e-300)
    r[~np.isfinite(r)] = 1e6
    return r


def _fit_family(fam: Family, P, y, idx_tr, i_special, max_starts=12):
    m = P.shape[1]
    others = [j for j in range(m) if j != i_special]
    logP = np.log(np.abs(P))
    best = None

    def model(theta, rows):
        params = theta[:fam.n_params]
        ex = theta[fam.n_params:]
        x = P[rows, i_special] if i_special is not None else np.ones(len(rows))
        out = fam.f(x, *params)
        if others:
            out = out * np.exp(logP[np.ix_(rows, others)] @ ex)
        return out

    for init in fam.inits[:max_starts]:
        for ex0 in ([0.0] * len(others), [1.0] * len(others)):
            th0 = np.array(list(init) + list(ex0), float)
            try:
                r = least_squares(lambda th: _rel_resid(model(th, idx_tr), y[idx_tr]), th0, method="lm",
                                  max_nfev=400 * (len(th0) + 1), xtol=1e-14, ftol=1e-14)
            except (ValueError, FloatingPointError):
                continue
            err = float(np.sqrt(np.mean(r.fun ** 2)))
            if best is None or err < best[0]:
                best = (err, r.x)
            if not others:
                break
    if best is None:
        return None
    return best[1], model


_BASES = None


def _ecost(e) -> float:
    """Naturalness cost of an exponent: 0 for none, then integers < halves < thirds < sixths."""
    if e == 0:
        return 0.0
    d = sp.fraction(sp.Rational(e))[1]
    return {1: 2.0, 2: 3.0, 3: 5.0, 6: 7.0}.get(int(d), 8.0) + 0.5 * (abs(float(e)) - 1 if abs(float(e)) > 1 else 0)


def identify_constant(v: float, rel_tol: float = 1e-8):
    """Closed form for a fitted number: r · π^a · 2^b · 3^c · ln2^d with small rational r.

    Exponents a, b, c run over multiples of 1/6 (covering √π, ∛3, …). Returns the
    simplest sympy expression reproducing v to `rel_tol`, or None."""
    global _BASES
    if v == 0 or not np.isfinite(v):
        return sp.Integer(0) if v == 0 else None
    if _BASES is None:
        bases = []
        sixths = [sp.Rational(k, 6) for k in range(-12, 13)]
        thirds = [sp.Rational(k, 6) for k in range(-6, 7)]
        for a in sixths:
            for b in thirds:
                for c in thirds:
                    for lg, lv, lc in ((sp.Integer(1), 1.0, 0), (sp.log(2), math.log(2), 3),
                                       (1 / sp.log(2), 1 / math.log(2), 3), (sp.log(10), math.log(10), 3),
                                       (1 / sp.log(10), 1 / math.log(10), 3)):
                        for e5 in (0, sp.Rational(1, 2), sp.Rational(-1, 2)):
                            val = math.pi ** float(a) * 2 ** float(b) * 3 ** float(c) * lv * 5 ** float(e5)
                            cx = _ecost(a) + _ecost(b) + _ecost(c) + lc + _ecost(e5) + 1
                            bases.append((cx, val, sp.pi ** a * 2 ** b * 3 ** c * lg * 5 ** e5))
        bases.sort(key=lambda t: t[0])
        _BASES = (np.array([t[0] for t in bases], float), np.array([t[1] for t in bases]), [t[2] for t in bases])
    cxs, vals, exprs = _BASES
    r = v / vals
    best = None
    for den in (1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 20, 24, 25, 30, 32, 36, 40, 48, 50, 60, 64, 100):
        nn = np.round(r * den)
        ok = (nn != 0) & (np.abs(nn) <= 2000) & (np.abs(r - nn / den) <= rel_tol * np.abs(r))
        if not ok.any():
            continue
        idx = np.where(ok)[0]
        score = cxs[idx] + math.log2(den) + np.log2(np.abs(nn[idx]) + 1)
        k = int(np.argmin(score))
        if best is None or score[k] < best[0]:
            best = (float(score[k]), sp.Rational(int(nn[idx[k]]), den) * exprs[idx[k]])
    if best is None or best[0] > 24:          # reject contrived closed forms
        return None
    return sp.nsimplify(best[1])


_CTOL = 1e-9          # relative tolerance for closed-form constants (raised for noisy data)


def _snap_value(v, kind):
    if not np.isfinite(v):
        return None
    if kind == "exp":
        for den in (1, 2, 3, 4, 6):
            n = round(v * den)
            if abs(v - n / den) < max(2e-3, 30 * _CTOL):
                return sp.Rational(n, den)
        return None
    if abs(v) < 1e-9:
        return sp.Integer(0)
    return identify_constant(v, _CTOL)


EXPONENT_SLOTS = {"a·x^p/(exp(b·x^r) + c)": [1, 3], "a·x^p": [1], "a + b·x^p": [2], "(a + b·x^p)^q": [2, 3], "a·exp(b·x^p)": [2],
                  "a/(exp(b·x^p) + c)": [2], "a·x^p·exp(b·x^r)": [1, 3], "a·cos(b·x)^p": [2],
                  "a·sin(x)^p": [1], "a·x^p/(b + x^p)": [2], "a·x^p/(1 + b·x)": [2]}


def _linear_candidates(P, Fy, idx_tr, idx_va, pis, gate=1e-6):
    """Families that are linear in their coefficients (solved exactly, no local minima):
    * multilinear rational  T(F) = N(π)/D(π), with T ∈ {F, F², 1/F, 1/F², √F} — covers Doppler shifts,
      velocity addition, Carnot COP, isostasy, time dilation, saturating laws;
    * additive linear/log    F = c₀ + Σ cᵢ πᵢ + Σ dᵢ ln πᵢ — covers pH, Henderson–Hasselbalch, phase rule."""
    n, m = P.shape
    out = []
    if m == 0 or m > 3:
        return out
    subsets = [s for k in range(m + 1) for s in itertools.combinations(range(m), k)]
    monos = np.array([np.prod(P[:, list(sub)], axis=1) if sub else np.ones(n) for sub in subsets]).T
    for tname, T, Tinv, Tsym in (("F", lambda f: f, lambda t: t, lambda e: e),
                                ("F^2", lambda f: f ** 2, lambda t: np.sqrt(np.abs(t)) * np.sign(Fy[0]), lambda e: sp.sqrt(e) * (1 if Fy[0] > 0 else -1)),
                                ("1/F", lambda f: 1 / f, lambda t: 1 / t, lambda e: 1 / e),
                                ("1/F^2", lambda f: 1 / f ** 2, lambda t: np.sign(Fy[0]) / np.sqrt(np.abs(t)), lambda e: (1 if Fy[0] > 0 else -1) / sp.sqrt(e)),
                                ("sqrt(F)", lambda f: np.sqrt(f), lambda t: t ** 2, lambda e: e ** 2)):
        with np.errstate(all="ignore"):
            t = T(Fy)
        if not np.all(np.isfinite(t)):
            continue
        # N(π) − t·(D(π) − 1) = t ;  unknowns: N coefficients (all monos) and D coefficients (non-constant monos)
        A = np.hstack([monos, -t[:, None] * monos[:, 1:]])
        w = 1 / np.maximum(np.abs(t), 1e-300)
        try:
            coef, *_ = np.linalg.lstsq((A * w[:, None])[idx_tr], (t * w)[idx_tr], rcond=None)
        except np.linalg.LinAlgError:
            continue
        k = monos.shape[1]
        num_c, den_c = coef[:k], np.concatenate([[1.0], coef[k:]])
        with np.errstate(all="ignore"):
            pred = Tinv((monos @ num_c) / (monos @ den_c))
        err = float(np.sqrt(np.mean(_rel_resid(pred[idx_va], Fy[idx_va]) ** 2)))
        if err < gate:
            sym_m = [sp.Mul(*[pis[i] for i in sub]) for sub in subsets]
            out.append(("rational", tname, num_c, den_c, sym_m, Tsym, err))
    # additive linear + log
    with np.errstate(all="ignore"):
        L = np.log(np.abs(P))
    A = np.hstack([np.ones((n, 1)), P, L])
    w = 1 / np.maximum(np.abs(Fy), 1e-300)
    coef, *_ = np.linalg.lstsq((A * w[:, None])[idx_tr], (Fy * w)[idx_tr], rcond=None)
    # prune negligible terms and refit for accurate coefficients
    keep = np.abs(coef) * np.abs(A).mean(axis=0) > 1e-9 * np.abs(Fy).mean()
    if keep.any() and not keep.all():
        c2, *_ = np.linalg.lstsq((A[:, keep] * w[:, None])[idx_tr], (Fy * w)[idx_tr], rcond=None)
        coef = np.zeros(A.shape[1])
        coef[keep] = c2
    err = float(np.sqrt(np.mean(_rel_resid((A @ coef)[idx_va], Fy[idx_va]) ** 2)))
    if err < gate:
        out.append(("additive", None, coef, None, [sp.Integer(1)] + list(pis) + [sp.log(p) for p in pis], None, err))
    return out


def _snap_linear(c, tol=1e-7):
    out = []
    scale = max(1e-300, max(abs(float(x)) for x in c))
    for v in c:
        if abs(v) < 1e-8 or abs(v) < 10 * _CTOL * scale:
            out.append(sp.Integer(0))
            continue
        g = identify_constant(float(v), max(1e-8, _CTOL))
        if g is None:
            return None
        out.append(g)
    return out


def regress(X: np.ndarray, y: np.ndarray, dims: list[Dim], target: Dim, names: list[str],
            seed: int = 0, tol_exact: float = 1e-6, noise: float = 0.0):
    """Find y = f(X). Returns dict with sympy expression (in `names`), error and method, or None.

    `noise` is the expected relative measurement error of y. With noise > 0 a closed-form model is
    accepted when it fits as well as the noise allows (residual ≤ 2.5 × noise), and constants are
    identified to the precision the noise permits."""
    global _CTOL
    _CTOL = max(1e-9, noise / 3)
    tol_exact = max(tol_exact, 2.5 * noise)
    fit_gate = max(1e-7, 2.5 * noise)
    rng = np.random.default_rng(seed)
    n = len(y)
    perm = rng.permutation(n)
    idx_tr, idx_va = perm[: int(0.75 * n)], perm[int(0.75 * n):]
    pa = pi_analysis(dims, target)
    if pa is None:
        return None
    mono_e, null = pa
    with np.errstate(all="ignore"):
        logX = np.log(np.abs(X))
        mono = np.exp(logX @ np.array([float(e) for e in mono_e]))
        Fy = y / mono
        P = np.exp(logX @ np.array(null, float).T) if null else np.zeros((n, 0))
    syms = [sp.Symbol(nm) for nm in names]
    mono_s = sp.Mul(*[s ** e for s, e in zip(syms, mono_e)])
    pis_real = [sp.Mul(*[s ** e for s, e in zip(syms, v)]) for v in null]
    pis = [sp.Dummy(f"pi{j}", positive=True) for j in range(len(null))]
    m = len(null)

    pool_exact = []

    def accept(F_expr, ferr, family):
        """Noiseless: return at once. Noisy: keep, choose the simplest adequate model at the end."""
        if noise == 0:
            return finish(F_expr, ferr, True, family)
        pool_exact.append((ferr, F_expr, family))
        return None

    def finish(F_expr, ferr, snapped, family):
        F_real = F_expr.subs(dict(zip(pis, pis_real)), simultaneous=True)
        expr = mono_s * F_real
        if snapped:
            try:
                expr = sp.powsimp(sp.simplify(expr), force=True)
            except Exception:
                pass
        return {"expr": expr, "val_err": ferr, "exact": bool(snapped and ferr is not None and ferr < tol_exact),
                "family": family, "pi_groups": [str(p) for p in pis_real], "monomial": str(mono_s)}

    # stage 0: no free Π — y is the monomial times a constant
    if m == 0:
        c = float(np.median(Fy))
        cs = _snap_value(c, "coef")
        if cs is not None and abs(float(cs) - c) <= tol_exact * abs(c) * 10:
            return finish(cs, float(np.sqrt(np.mean(_rel_resid(np.full(n, float(cs)), Fy) ** 2))), True, "constant")
        return finish(sp.Float(c, 10), 0.0, False, "constant")

    approx = []
    # stage 1: exactly solvable (linear-in-coefficients) families
    for kind, tname, a, b, sym_m, Tsym, err in _linear_candidates(P, Fy, idx_tr, idx_va, pis, max(1e-6, 2.5 * noise)):
        if kind == "rational":
            na, nb = _snap_linear(a), _snap_linear(b)
            if na is not None and nb is not None:
                F = Tsym(sp.Add(*[c * s for c, s in zip(na, sym_m)]) / sp.Add(*[c * s for c, s in zip(nb, sym_m)]))
                e2 = _eval_err(F, pis, P, Fy)
                if e2 is not None and e2 < tol_exact:
                    r_ = accept(F, e2, f"rational({tname})")
                    if r_:
                        return r_
            approx.append((err, Tsym(sp.Add(*[sp.Float(c, 10) * s for c, s in zip(a, sym_m)]) /
                                     sp.Add(*[sp.Float(c, 10) * s for c, s in zip(b, sym_m)])), "rational"))
        else:
            na = _snap_linear(a)
            if na is not None:
                F = sp.Add(*[c * s for c, s in zip(na, sym_m)])
                e2 = _eval_err(F, pis, P, Fy)
                if e2 is not None and e2 < tol_exact:
                    r_ = accept(F, e2, "additive(lin+log)")
                    if r_:
                        return r_
            approx.append((err, sp.Add(*[sp.Float(c, 10) * s for c, s in zip(a, sym_m)]), "additive"))

    # stage 2b: families coupling two Π groups (variable exponents, scaled logarithms)
    if m >= 2:
        logPm = np.log(np.abs(P))
        pair_fams = [
            ("a + b·x^(c + d·z)", 4, lambda x, z, a, b, c, d: a + b * np.power(x, c + d * z),
             lambda x, z, a, b, c, d: a + b * x ** (c + d * z), [[1, -1, 1, -1], [0, 1, 0, 1], [1, 1, 0, 1]], [3]),
            ("x^(b·z)/(a + x^(b·z))", 2, lambda x, z, a, b: np.power(x, b * z) / (a + np.power(x, b * z)),
             lambda x, z, a, b: x ** (b * z) / (a + x ** (b * z)), [[1, 1]], []),
            ("a + b·log(x)·z^c", 3, lambda x, z, a, b, c: a + b * np.log(x) * np.power(z, c),
             lambda x, z, a, b, c: a + b * sp.log(x) * z ** c, [[1, -1, -1], [0, 1, -1], [1, 1, 1], [0, 1, 1]], [2]),
        ]
        for name, npar, f, fe, inits, exp_slots in pair_fams:
            for i, j in itertools.permutations(range(m), 2):
                others = [k for k in range(m) if k not in (i, j)]

                def model(th, rows, f=f, npar=npar, i=i, j=j, others=others):
                    out = f(P[rows, i], P[rows, j], *th[:npar])
                    return out * np.exp(logPm[np.ix_(rows, others)] @ th[npar:]) if others else out
                for init in inits:
                    th0 = np.array(list(init) + [0.0] * len(others), float)
                    try:
                        r = least_squares(lambda th: _rel_resid(model(th, idx_tr), Fy[idx_tr]), th0, method="lm",
                                          max_nfev=2000, xtol=1e-14, ftol=1e-14)
                    except (ValueError, FloatingPointError):
                        continue
                    err = float(np.sqrt(np.mean(_rel_resid(model(r.x, idx_va), Fy[idx_va]) ** 2)))
                    if err < fit_gate:
                        vals = [_snap_value(v, "exp" if k in exp_slots else "coef") for k, v in enumerate(r.x[:npar])]
                        ovals = [_snap_value(v, "exp") for v in r.x[npar:]]
                        if all(v is not None for v in vals + ovals):
                            F = fe(pis[i], pis[j], *vals) * sp.Mul(*[pis[k] ** e for k, e in zip(others, ovals)])
                            e2 = _eval_err(F, pis, P, Fy)
                            if e2 is not None and e2 < tol_exact:
                                r_ = accept(F, e2, name)
                                if r_:
                                    return r_
                        approx.append((err, fe(pis[i], pis[j], *[sp.Float(v, 10) for v in r.x[:npar]]) *
                                       sp.Mul(*[pis[k] ** sp.Float(e, 8) for k, e in zip(others, r.x[npar:])]), name))
                        break

    # stage 2: nonlinear families, simplest first, stopping at the first exact snap
    cands = []
    fams = families()
    for fam in fams:
        specials = range(m) if fam.special else [None]
        for i in specials:
            res = _fit_family(fam, P, Fy, idx_tr, i)
            if res is None:
                continue
            theta, model = res
            err = float(np.sqrt(np.mean(_rel_resid(model(theta, idx_va), Fy[idx_va]) ** 2)))
            cands.append((fam, i, theta, err, fam.n_params + m - 1))
            if err < fit_gate:
                out = _to_expr(fam, i, theta, pis, m, P, Fy, idx_va, tol_exact)
                if out is not None and out[2]:
                    r_ = accept(out[0], out[1], fam.name)
                    if r_:
                        return r_
    # stage 3: sum of two power terms over all Π
    logP = np.log(np.abs(P))
    for sgn in (1, -1):
        def mdl(th, rows):
            return th[0] * np.exp(logP[rows] @ th[2:2 + m]) + th[1] * np.exp(logP[rows] @ th[2 + m:])
        for e0 in itertools.product((0, 1, 2, -1), repeat=min(m, 2)):
            th0 = np.array([1, sgn] + [0] * m + list(e0) + [0] * (m - len(e0)), float)
            try:
                r = least_squares(lambda th: _rel_resid(mdl(th, idx_tr), Fy[idx_tr]), th0, method="lm",
                                  max_nfev=3000, xtol=1e-14, ftol=1e-14)
            except (ValueError, FloatingPointError):
                continue
            err = float(np.sqrt(np.mean(_rel_resid(mdl(r.x, idx_va), Fy[idx_va]) ** 2)))
            cands.append(("sum2", None, r.x, err, 2 + 2 * m))
            if err < fit_gate:
                out = _to_expr("sum2", None, r.x, pis, m, P, Fy, idx_va, tol_exact)
                if out is not None and out[2]:
                    r_ = accept(out[0], out[1], "sum2")
                    if r_:
                        return r_
    if pool_exact:
        floor = min(e for e, _, _ in pool_exact)
        raw_floor = min([c[3] for c in cands] + [floor])
        ok = [t for t in pool_exact if t[0] <= max(1.05 * raw_floor, floor * 1.02) + 1e-12]
        e, F, fam = min(ok, key=lambda t: (sp.count_ops(t[1]), t[0]))
        return finish(F, e, True, fam)
    cands.sort(key=lambda c: c[3])
    best_nl = None
    for fam, i, theta, err, k in cands[:6]:
        out = _to_expr(fam, i, theta, pis, m, P, Fy, idx_va, tol_exact)
        if out is not None:
            best_nl = (out[1] if out[1] is not None else err, out[0], fam if isinstance(fam, str) else fam.name)
            break
    pool = approx + ([best_nl] if best_nl else [])
    if not pool:
        return None
    err, F, fam = min(pool, key=lambda t: t[0] if t[0] is not None else 1e9)
    return finish(F, err, False, fam)


def _to_expr(fam, i, theta, pis, m, P, Fy, idx_va, tol):
    """Build sympy F(π); try snapping constants; keep the snapped form only if it stays exact."""
    if fam == "constant":
        c = _snap_value(theta[0], "coef")
        if c is not None and abs(float(c) - theta[0]) <= tol * max(1, abs(theta[0])) * 10:
            return c, float(np.sqrt(np.mean(_rel_resid(np.full(len(Fy), float(c)), Fy) ** 2))), True
        return sp.Float(theta[0], 10), 0.0, False
    x = sp.Symbol("_x")
    if fam == "sum2":
        a, b = theta[0], theta[1]
        p, r = theta[2:2 + m], theta[2 + m:]
        raw = a * sp.Mul(*[pi ** float(e) for pi, e in zip(pis, p)]) + b * sp.Mul(*[pi ** float(e) for pi, e in zip(pis, r)])
        sn = [_snap_value(a, "coef"), _snap_value(b, "coef")] + [_snap_value(e, "exp") for e in list(p) + list(r)]
        if all(v is not None for v in sn):
            F = sn[0] * sp.Mul(*[pi ** e for pi, e in zip(pis, sn[2:2 + m])]) + \
                sn[1] * sp.Mul(*[pi ** e for pi, e in zip(pis, sn[2 + m:])])
            err = _eval_err(F, pis, P, Fy)
            if err is not None and err < tol:
                return F, err, True
        return raw, None, False
    params = list(theta[:fam.n_params])
    others = list(theta[fam.n_params:])
    oth_idx = [j for j in range(m) if j != i]
    slots = EXPONENT_SLOTS.get(fam.name, [])
    snapped = []
    for k, v in enumerate(params):
        snapped.append(_snap_value(v, "exp" if k in slots else "coef"))
    osn = [_snap_value(v, "exp") for v in others]
    xi = pis[i] if i is not None else sp.Integer(1)
    if all(v is not None for v in snapped + osn):
        F = fam.expr(xi, *snapped) * sp.Mul(*[pis[j] ** e for j, e in zip(oth_idx, osn)])
        err = _eval_err(F, pis, P, Fy)
        if err is not None and err < tol:
            return F, err, True
    F = fam.expr(xi, *[sp.Float(v, 10) for v in params]) * \
        sp.Mul(*[pis[j] ** sp.Float(e, 8) for j, e in zip(oth_idx, others)])
    return F, _eval_err(F, pis, P, Fy), False


def _eval_err(F, pis, P, Fy):
    try:
        f = sp.lambdify(pis, F, "numpy")
        with np.errstate(all="ignore"):
            pred = np.asarray(f(*[P[:, j] for j in range(len(pis))]), dtype=complex)
    except Exception:
        return None
    if np.abs(pred.imag).max() > 1e-9 * np.abs(pred).max():
        return None
    r = _rel_resid(pred.real * np.ones(len(Fy)), Fy)
    return float(np.sqrt(np.mean(r ** 2)))
