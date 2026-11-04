"""Two-variable physics discovery: sharp, machine-proved bounds between physical quantities
that depend on two physical parameters at once.

Systems (each over its physical domain):
  two-body decay         a = m1/M, b = m2/M        (a + b < 1)
  collision              m = m1/m2, e = restitution (0 < m, e < 1)
  driven oscillator      r = ω/ω0, z = damping ratio (r < 2, z < 1)
  velocity addition      u, v = speeds / c          (u, v < 1)
  Compton scattering     x = E/(m_e c²), c = 1 − cos θ   (x < 2, c < 2)

Each round: the local 14B model proposes new quantities (optional); Euresis validates
them; for every pair (f, g) it finds inf f/g over the 2-D domain (grid + local
refinement), snaps it to an exact rational k, and sends f ≥ k·g with the domain to the
verification gate (Z3 with exact square roots). A *discovery* is
  proved · sharp to 1e-6 · equality at an interior point · depends on BOTH variables ·
  not a known result · not implied by proved bounds · not the same inequality as an
  earlier discovery.
Runs until `data/STOP` exists or the segment's time budget ends.
"""
from __future__ import annotations

import json
import random
import time
from fractions import Fraction

import numpy as np
import sympy as sp
from scipy.optimize import minimize

from . import gate
from .physics_discover import parse_items
from .registry import ROOT, Registry

STATE = ROOT / "space" / "physics2_state.json"
LOG = ROOT / "space" / "physics2_log.md"
STOP = ROOT / "data" / "STOP"

FAMILIES = {
    "two-body decay": {
        "vars": ("a", "b"), "bounds": ((0, 1), (0, 1)),
        "meaning": "a particle of mass M at rest decays into masses m1 = aM and m2 = bM (c = 1)",
        "assumptions": ["a < 1", "b < 1", "a + b < 1"],
        "region": lambda a, b: a + b < 1,
        "quantities": {
            "momentum of each product / (Mc)": "sqrt((1 - (a + b)**2)*(1 - (a - b)**2))/2",
            "energy of product 1 / (Mc²)": "(1 + a**2 - b**2)/2",
            "energy of product 2 / (Mc²)": "(1 - a**2 + b**2)/2",
            "kinetic energy released Q / (Mc²)": "1 - a - b",
            "kinetic energy of product 1 / (Mc²)": "((1 - a)**2 - b**2)/2",
            "speed of product 1 / c": "sqrt((1 - (a + b)**2)*(1 - (a - b)**2))/(1 + a**2 - b**2)",
            "speed of product 2 / c": "sqrt((1 - (a + b)**2)*(1 - (a - b)**2))/(1 - a**2 + b**2)",
            "Lorentz factor of product 1": "(1 + a**2 - b**2)/(2*a)",
        }},
    "collision": {
        "vars": ("m", "e"), "bounds": ((0, 1), (0, 1)),
        "meaning": "head-on collision of m1 (moving) with m2 (at rest), m = m1/m2, coefficient of restitution e",
        "assumptions": ["m < 1", "e < 1"], "region": None,
        "quantities": {
            "target speed / initial speed": "(1 + e)*m/(1 + m)",
            "momentum transferred / initial momentum": "(1 + e)/(1 + m)",
            "fraction of kinetic energy lost": "(1 - e**2)/(1 + m)",
            "fraction of kinetic energy given to the target": "(1 + e)**2*m/(1 + m)**2",
            "speed of the centre of mass / initial speed": "m/(1 + m)",
            "relative speed after / relative speed before": "e",
        }},
    "driven oscillator": {
        "vars": ("r", "z"), "bounds": ((0, 2), (0, 1)),
        "meaning": "harmonic oscillator driven at r = ω/ω0 with damping ratio z, steady state",
        "assumptions": ["r < 2", "z < 1"], "region": None,
        "quantities": {
            "amplitude / static deflection": "1/sqrt((1 - r**2)**2 + (2*z*r)**2)",
            "transmissibility": "sqrt((1 + (2*z*r)**2)/((1 - r**2)**2 + (2*z*r)**2))",
            "velocity amplitude / (ω0 × static deflection)": "r/sqrt((1 - r**2)**2 + (2*z*r)**2)",
            "acceleration amplitude / (ω0² × static deflection)": "r**2/sqrt((1 - r**2)**2 + (2*z*r)**2)",
            "mean absorbed power (normalised)": "2*z*r**2/((1 - r**2)**2 + (2*z*r)**2)",
            "quality factor": "1/(2*z)",
        }},
    "velocity addition": {
        "vars": ("u", "v"), "bounds": ((0, 1), (0, 1)),
        "meaning": "a body moves at u (in units of c) in a frame that itself moves at v, same direction",
        "assumptions": ["u < 1", "v < 1"], "region": None,
        "quantities": {
            "composed speed / c": "(u + v)/(1 + u*v)",
            "Galilean sum / c": "u + v",
            "Lorentz factor of the composed motion": "(1 + u*v)/(sqrt(1 - u**2)*sqrt(1 - v**2))",
            "product of the two Lorentz factors": "1/(sqrt(1 - u**2)*sqrt(1 - v**2))",
            "Doppler factor of the composed motion": "sqrt((1 + u)/(1 - u))*sqrt((1 + v)/(1 - v))",
            "kinetic energy of the composed motion / mc²": "(1 + u*v)/(sqrt(1 - u**2)*sqrt(1 - v**2)) - 1",
            "sum of the two kinetic energies / mc²": "1/sqrt(1 - u**2) + 1/sqrt(1 - v**2) - 2",
        }},
    "Compton scattering": {
        "vars": ("x", "c"), "bounds": ((0, 2), (0, 2)),
        "meaning": "photon of energy E = x·m_e c² scattered by a free electron at angle θ, c = 1 − cos θ",
        "assumptions": ["x < 2", "c < 2"], "region": None,
        "quantities": {
            "scattered photon energy / initial energy": "1/(1 + x*c)",
            "electron kinetic energy / photon energy": "x*c/(1 + x*c)",
            "scattered photon energy / (m_e c²)": "x/(1 + x*c)",
            "electron kinetic energy / (m_e c²)": "x**2*c/(1 + x*c)",
            "wavelength shift / Compton wavelength": "c",
            "photon energy / (m_e c²)": "x",
        }},
    # ------------------------------------------------------------------ economics
    "Cournot duopoly": {
        "subject": "economics", "vars": ("c1", "c2"), "bounds": ((0, 0.5), (0, 0.5)),
        "meaning": "two firms compete in quantities; linear demand P = 1 − Q; marginal costs c1, c2",
        "assumptions": ["c1 < 1/2", "c2 < 1/2"], "region": None,
        "quantities": {
            "output of firm 1": "(1 - 2*c1 + c2)/3",
            "output of firm 2": "(1 - 2*c2 + c1)/3",
            "market price": "(1 + c1 + c2)/3",
            "profit of firm 1": "(1 - 2*c1 + c2)**2/9",
            "profit of firm 2": "(1 - 2*c2 + c1)**2/9",
            "consumer surplus": "(2 - c1 - c2)**2/18",
            "total industry profit": "((1 - 2*c1 + c2)**2 + (1 - 2*c2 + c1)**2)/9",
            "firm 1's profit as a monopolist": "(1 - c1)**2/4",
        }},
    "insurance and risk": {
        "subject": "economics", "vars": ("p", "L"), "bounds": ((0, 1), (0, 1)),
        "meaning": "a risk-averse person (utility √wealth, wealth 1) loses a fraction L of wealth with probability p",
        "assumptions": ["p < 1", "L < 1"], "region": None,
        "quantities": {
            "expected wealth": "1 - p*L",
            "expected utility": "p*sqrt(1 - L) + 1 - p",
            "certainty equivalent": "(p*sqrt(1 - L) + 1 - p)**2",
            "risk premium": "1 - p*L - (p*sqrt(1 - L) + 1 - p)**2",
            "actuarially fair insurance premium": "p*L",
            "maximum premium the person would pay for full insurance": "1 - (p*sqrt(1 - L) + 1 - p)**2",
            "variance of wealth": "p*(1 - p)*L**2",
        }},
    "auction with a reserve price": {
        "subject": "economics", "vars": ("r", "v"), "bounds": ((0, 1), (0, 1)),
        "meaning": "second-price auction, two bidders with values uniform on [0, 1], reserve price r, "
                   "seller values the item at v",
        "assumptions": ["r < 1", "v < 1"], "region": None,
        "quantities": {
            "expected revenue": "1/3 + r**2 - 4*r**3/3",
            "seller's expected payoff": "1/3 + r**2 - 4*r**3/3 + v*r**2",
            "probability the item is not sold": "r**2",
            "expected total bidder surplus": "1/3 - r**2 + 2*r**3/3",
            "expected total welfare": "2*(1 - r**3)/3 + v*r**2",
            "welfare with the efficient reserve (r = v)": "2/3 + v**3/3",
        }},
}

KNOWN = {
    ("velocity addition", "Galilean sum / c", "composed speed / c"): "relativistic composition never exceeds the Galilean sum",
    ("velocity addition", "Lorentz factor of the composed motion", "product of the two Lorentz factors"):
        "γ_w = γ_u γ_v (1 + uv)",
}


# ------------------------------------------------------------------ helpers
def _u():
    lo = np.logspace(-4, np.log10(0.5), 70)
    return np.unique(np.concatenate([lo, 1 - lo]))


U = _u()


def syms(fam):
    return tuple(sp.Symbol(n, positive=True) for n in FAMILIES[fam]["vars"])


def mesh(fam):
    F = FAMILIES[fam]
    (l1, h1), (l2, h2) = F["bounds"]
    X, Y = np.meshgrid(l1 + (h1 - l1) * U, l2 + (h2 - l2) * U, indexing="ij")
    X, Y = X.ravel(), Y.ravel()
    if F["region"] is not None:
        keep = F["region"](X, Y)
        X, Y = X[keep], Y[keep]
    return X, Y


def evaluate(fam, expr, X, Y):
    s1, s2 = syms(fam)
    E = sp.sympify(expr, locals={s1.name: s1, s2.name: s2}) if isinstance(expr, str) else expr
    with np.errstate(all="ignore"):
        out = np.asarray(sp.lambdify((s1, s2), E, "numpy")(X, Y), float)
    return np.broadcast_to(out, X.shape).astype(float)


def load_state() -> dict:
    if STATE.exists():
        st = json.loads(STATE.read_text())
        for k, v in FAMILIES.items():
            st["families"].setdefault(k, dict(v["quantities"]))
        return st
    return {"families": {k: dict(v["quantities"]) for k, v in FAMILIES.items()}, "rejected": [], "tried": [],
            "edges": [], "rounds": 0, "discoveries": [], "rediscoveries": []}


def save_state(st):
    STATE.write_text(json.dumps(st, indent=1) + "\n")


def log(msg, echo=print):
    echo(msg)
    with LOG.open("a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


# --------------------------------------------------------------- validation
def _allowed(E):
    for node in sp.preorder_traversal(E):
        if isinstance(node, sp.Function) or node.is_Function:
            return False
        if node.is_Pow and sp.Rational(node.exp).q not in (1, 2):
            return False
    return True


def validate(fam, expr, known):
    s1, s2 = syms(fam)
    try:
        E = sp.sympify(expr.replace("^", "**"), locals={s1.name: s1, s2.name: s2})
    except Exception:
        return None, "does not parse"
    if not isinstance(E, sp.Expr) or not E.free_symbols or E.free_symbols - {s1, s2}:
        return None, f"must depend only on {s1}, {s2}"
    try:
        if not _allowed(E):
            return None, "only + − × ÷, integer powers and square roots (so the prover can decide it)"
    except (TypeError, ValueError):
        return None, "only rational exponents allowed"
    X, Y = mesh(fam)
    vals = evaluate(fam, E, X, Y)
    if not np.all(np.isfinite(vals)):
        return None, "not finite on the whole physical domain"
    if vals.min() <= 0:
        return None, "not positive on the physical domain"
    sel = slice(None, None, 11)
    K = {n: evaluate(fam, s, X, Y) for n, s in known.items()}
    K.update({f"1/({n})": 1 / x for n, x in list(K.items())})
    names = list(K)
    one = np.ones_like(vals)
    for i, ni in enumerate(names):
        for nj in [None] + names[i + 1:]:
            A = np.stack([one, K[ni]] + ([K[nj]] if nj else []), 1)[sel]
            if not np.all(np.isfinite(A)):
                continue
            coef, *_ = np.linalg.lstsq(A, vals[sel], rcond=None)
            if np.max(np.abs(A @ coef - vals[sel]) / np.maximum(1.0, np.abs(vals[sel]))) < 1e-7:
                return None, f"affine combination of known quantities ({ni}{', ' + nj if nj else ''})"
    base = [n for n in names if not n.startswith("1/(")]
    Lg = np.stack([one] + [np.log(K[n]) for n in base], 1)[sel]
    if np.all(np.isfinite(Lg)):
        lv = np.log(vals[sel])
        cf, *_ = np.linalg.lstsq(Lg, lv, rcond=None)
        if np.abs(Lg @ cf - lv).max() < 1e-7:
            return None, "a power or product of known quantities"
    return E, "ok"


# ------------------------------------------------------------- proposals
def propose_llm(fam, st, n=4, echo=print):
    from . import local_llm
    F = FAMILIES[fam]
    v1, v2 = F["vars"]
    known = st["families"][fam]
    rej = [r for r in st["rejected"] if r.get("family") == fam][-8:]
    msg = (f"Physical system: {fam}. {F['meaning']}. Variables {v1}, {v2}; domain: {', '.join(F['assumptions'])}, "
           f"both positive.\nKnown dimensionless quantities (name: SymPy expression):\n"
           + "\n".join(f"  {k}: {x}" for k, x in known.items())
           + f"\n\nPropose {n} OTHER dimensionless quantities that physicists actually use for this system — real "
           f"textbook formulas, named precisely — depending on BOTH {v1} and {v2}. Use only + - * /, integer powers "
           "(**) and sqrt. Each must be positive and finite on the domain and not a simple sum or product of the "
           "known ones.\n"
           + ("Rejected before (reason in brackets):\n" + "\n".join(f"  {r['expr']} [{r['why']}]" for r in rej) + "\n"
              if rej else "")
           + 'Reply with JSON only: [{"name": "...", "expr": "..."}, ...]')
    r = local_llm.complete("You are the physics idea generator of Euresis. You propose; a theorem prover decides "
                           "what is true. Reply with JSON only.", [{"role": "user", "content": msg}],
                           think=False, max_tokens=800, temperature=0.8, log=echo)
    items = parse_items(r["text"] or r["raw"])
    echo(f"  model proposed {len(items)} quantities for {fam} in {r['seconds']} s")
    if not items:
        log(f"model reply could not be parsed ({fam}): {(r['raw'] or '')[:300]!r}", echo)
    return items[:n]


# ------------------------------------------------------------------ bounds
def _snap(x):
    fr = Fraction(x).limit_denominator(64)
    if abs(float(fr) - x) <= 2e-5 * max(1.0, abs(x)) and fr != 0:
        return sp.Rational(fr.numerator, fr.denominator)
    return None


def ratio_min(fam, f, g):
    """inf of f/g over the domain: grid search, then local refinement from the best grid points."""
    F = FAMILIES[fam]
    X, Y = mesh(fam)
    s1, s2 = syms(fam)
    with np.errstate(all="ignore"):
        rfun = sp.lambdify((s1, s2), f / g, "numpy")
        R = np.asarray(rfun(X, Y), float)
    R = np.broadcast_to(R, X.shape)
    fin = R[np.isfinite(R)]
    if fin.size < R.size // 2 or fin.max() - fin.min() < 1e-9 * max(1.0, abs(fin).max()):
        return None                      # undefined, or a constant ratio (an identity, not a bound)
    order = np.argsort(np.where(np.isfinite(R), R, np.inf))[:4]
    (l1, h1), (l2, h2) = F["bounds"]

    def obj(p):
        x, y = p
        if not (l1 < x < h1 and l2 < y < h2) or (F["region"] is not None and not F["region"](x, y)):
            return 1e300
        with np.errstate(all="ignore"):
            val = float(rfun(x, y))
        return val if np.isfinite(val) else 1e300
    best = (float(R[order[0]]), float(X[order[0]]), float(Y[order[0]]))
    for i in order:
        res = minimize(obj, [X[i], Y[i]], method="Nelder-Mead", options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 4000})
        if res.fun < best[0]:
            best = (float(res.fun), float(res.x[0]), float(res.x[1]))
    # does the ratio depend on both variables?
    Rm = R.copy()
    both = True
    for axis_var in (X, Y):
        groups = {}
        for val, key in zip(Rm, np.round(axis_var, 12)):
            if np.isfinite(val):
                groups.setdefault(key, []).append(val)
        spread = max(((max(v) - min(v)) / max(1.0, abs(max(v))) for v in groups.values() if len(v) > 1), default=0.0)
        if spread < 1e-9:
            both = False                  # constant along the other variable
    return best, both


def isolated_minimum(fam, f, g, x, y) -> bool:
    """Equality at an isolated point, not along a curve: the Hessian of f/g at the minimum is positive definite.
    (Bounds tight along a whole curve are one-variable inequalities in disguise, e.g. γ ≥ 2β with β = β(a, b).)"""
    s1, s2 = syms(fam)
    rf = sp.lambdify((s1, s2), f / g, "math")
    (l1, h1), (l2, h2) = FAMILIES[fam]["bounds"]
    hx, hy = 2e-4 * (h1 - l1), 2e-4 * (h2 - l2)
    try:
        c = rf(x, y)
        fxx = (rf(x + hx, y) - 2 * c + rf(x - hx, y)) / hx ** 2
        fyy = (rf(x, y + hy) - 2 * c + rf(x, y - hy)) / hy ** 2
        fxy = (rf(x + hx, y + hy) - rf(x + hx, y - hy) - rf(x - hx, y + hy) + rf(x - hx, y - hy)) / (4 * hx * hy)
    except (ValueError, ZeroDivisionError):
        return False
    ev = np.linalg.eigvalsh(np.array([[fxx, fxy], [fxy, fyy]]))
    return bool(ev.min() > 1e-4 * max(abs(ev).max(), 1e-12))


def interior(fam, x, y):
    F = FAMILIES[fam]
    (l1, h1), (l2, h2) = F["bounds"]
    m1, m2 = 1e-3 * (h1 - l1), 1e-3 * (h2 - l2)
    ok = l1 + m1 < x < h1 - m1 and l2 + m2 < y < h2 - m2
    if ok and fam == "two-body decay":
        ok = x + y < 1 - 1e-3
    return ok


def prove(fam, f, g, k):
    s1, s2 = syms(fam)
    asm = FAMILIES[fam]["assumptions"]
    payload = {"claim": f"{f} >= {k}*({g})", "symbols": [s1.name, s2.name], "assumptions": asm}
    status, _ = gate.verify_physics_relation(payload)
    sharp = False
    if status == "proved":
        k2 = k * (1 + sp.Rational(1, 10 ** 6))
        sharp = gate.verify_physics_relation({"claim": f"{f} >= {k2}*({g})", "symbols": [s1.name, s2.name],
                                              "assumptions": asm})[0] == "refuted"
    return status, payload, sharp


_CMP = slice(None, None, 97)


def ratio_samples(fam, f, g):
    X, Y = mesh(fam)
    return [float(x) for x in evaluate(fam, f / g, X, Y)[_CMP]]


def equivalent(st, fam, rs):
    r = np.array(rs)
    for d in st["discoveries"]:
        if d["family"] != fam:
            continue
        q = np.array(d["ratio"])
        for w in (r / q, r * q):
            if np.all(np.isfinite(w)) and w.max() - w.min() < 1e-8 * max(1.0, abs(w).max()):
                return f"same inequality as earlier discovery {d['claim']}"
    return ""


def implied(st, fam, fn, gn, k):
    E = {(e["f"], e["g"]): sp.Rational(e["k"]) for e in st["edges"] if e["family"] == fam}
    if (fn, gn) in E and E[(fn, gn)] >= k:
        return "a bound at least as strong is already proved"
    for (x, h), k1 in E.items():
        if x == fn and (h, gn) in E and k1 * E[(h, gn)] >= k:
            return f"follows from bounds through '{h}'"
    return ""


# ---------------------------------------------------------------- one round
def run_round(st, reg, use_llm, echo=print, max_pairs=24):
    st["rounds"] += 1
    fams = list(FAMILIES)
    fam = fams[(st["rounds"] - 1) % len(fams)]
    log(f"round {st['rounds']}: {fam}", echo)
    exprs = st["families"][fam]
    new = {}
    if use_llm:
        for item in propose_llm(fam, st, echo=echo):
            E, why = validate(fam, item["expr"], {**exprs, **new})
            name = str(item.get("name") or item["expr"])[:80] + " [model-proposed; physical meaning unverified]"
            if E is None:
                st["rejected"].append({"family": fam, "expr": item["expr"][:100], "why": why})
                echo(f"    rejected: {item['expr'][:70]}  [{why}]")
            elif name not in exprs and name not in new:
                new[name] = str(E)
                echo(f"    accepted: {name} = {E}")
    exprs.update(new)
    s1, s2 = syms(fam)
    loc = {s1.name: s1, s2.name: s2}
    pairs = [(x, y) for x in exprs for y in exprs if x != y and f"{fam}|{x}|{y}" not in st["tried"]]
    pairs.sort(key=lambda p: (p[0] not in new and p[1] not in new, random.Random(st["rounds"]).random()))
    found = []
    for fn, gn in pairs[:max_pairs]:
        st["tried"].append(f"{fam}|{fn}|{gn}")
        f, g = sp.sympify(exprs[fn], locals=loc), sp.sympify(exprs[gn], locals=loc)
        res = ratio_min(fam, f, g)
        if res is None:
            continue
        (val, x0, y0), both = res
        if not (0 < val < 1e6):
            continue
        k = _snap(val)
        if k is None:
            continue
        status, payload, sharp = prove(fam, f, g, k)
        if status != "proved" or not sharp:
            continue
        inn = interior(fam, x0, y0)
        where = (f"equality at ({s1}, {s2}) ≈ ({x0:.6g}, {y0:.6g})" if inn
                 else f"tight only at the edge of the domain, near ({x0:.3g}, {y0:.3g})")
        subj = FAMILIES[fam].get("subject", "physics")
        stmt = f"[{subj}: {fam}] {fn} ≥ {k} × {gn}   on {', '.join(FAMILIES[fam]['assumptions'])} ({where})"
        cid = reg.add("physics-relation", stmt, payload, source=f"physics_discover2 round {st['rounds']}")
        gate.check(reg, cid, log=lambda *a: None)
        if reg.get(cid)["status"] != "proved":
            continue
        rs = ratio_samples(fam, f, g)
        known = KNOWN.get((fam, fn, gn))
        chain = implied(st, fam, fn, gn, k)
        st["edges"].append({"family": fam, "f": fn, "g": gn, "k": str(k)})
        if known:
            reg.set_novelty(cid, f"known ({known})")
            st["rediscoveries"].append({"claim": cid, "statement": stmt, "known": known})
            echo(f"    rediscovered known law: {stmt}")
        elif chain:
            reg.set_novelty(cid, f"follows from proved bounds: {chain}")
        elif not inn:
            reg.set_novelty(cid, "boundary comparison (tight only at the edge of the domain) — proved, not counted")
        elif not both:
            reg.set_novelty(cid, "depends on one variable only — a one-variable bound, not counted here")
            echo(f"    proved but one-variable only: {stmt}")
        elif not isolated_minimum(fam, f, g, x0, y0):
            reg.set_novelty(cid, "equality holds along a whole curve — a one-variable inequality in disguise; "
                                 "proved, not counted")
            echo(f"    proved but equality along a curve (one-variable in disguise): {stmt}")
        elif (eq := equivalent(st, fam, rs)):
            reg.set_novelty(cid, f"follows from proved bounds: {eq}")
            echo(f"    proved but {eq}")
        else:
            caveat = ("; involves a model-proposed quantity whose physical meaning is unverified"
                      if "model-proposed" in fn + gn else "")
            reg.set_novelty(cid, "not a known result in Euresis' knowledge; not implied by proved bounds; "
                                 "physics literature unchecked (arXiv unreachable from this environment)" + caveat)
            rec = {"claim": cid, "statement": stmt, "family": fam, "round": st["rounds"], "ratio": rs,
                   "equality_at": [x0, y0]}
            st["discoveries"].append(rec)
            found.append(rec)
            log(f"DISCOVERY (proved, sharp to 1e-6, two-variable): {stmt}  [{cid}]", echo)
    return found


def run(minutes=100.0, use_llm=None, echo=print):
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
