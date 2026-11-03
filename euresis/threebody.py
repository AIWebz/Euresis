"""Live model of known science: Newtonian gravity — and a search for new periodic three-body orbits.

The model is Euresis' own law of universal gravitation, F = G m₁ m₂ / r², integrated
numerically. Exploration targets one of physics' oldest frontiers: periodic
solutions of the three-body problem.

Setting (the standard one, so results are comparable with the literature):
equal masses m = 1, G = 1, start at (−1, 0), (1, 0), (0, 0) with velocities
(v₁, v₂), (v₁, v₂), (−2v₁, −2v₂) — zero total momentum and angular momentum.

1. **Screen** — integrate a grid of (v₁, v₂) simultaneously (vectorised 4th-order
   symplectic integrator) and record how closely each motion returns to its start.
2. **Refine** — Newton/least-squares on (v₁, v₂, T) with a high-accuracy adaptive
   integrator (DOP853, tol 1e-12) until the orbit closes to < 1e-8.
3. **Check novelty** — compare every confirmed orbit (v₁, v₂, T, and multiples of T)
   with Li & Liao's catalogue of 695 equal-mass families (github.com/sjtu-liao/three-body).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import re
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "external" / "threebody" / "three-body" / "three-body-pictures.md"
OUT = ROOT / "space" / "threebody"
X0 = np.array([-1.0, 0.0, 1.0, 0.0, 0.0, 0.0])


def initial_state(v1, v2):
    return np.concatenate([X0, [v1, v2, v1, v2, -2 * v1, -2 * v2]])


def energy(v1, v2):
    return 3 * (v1 ** 2 + v2 ** 2) - 2.5


# ------------------------------------------------------------ catalogue
def load_catalog():
    s = CATALOG.read_text()
    rows = re.findall(r"<th>([^<]*<sup>.*?)</th>\s*<th>\s*([-\d.]+)</th>\s*<th>\s*([-\d.]+)</th>\s*<th>\s*([-\d.]+)</th>\s*<th>\s*([-\d.]+)</th>", s, re.S)
    out = []
    for name, v1, v2, T, Ts in rows:
        nm = re.sub(r"<[^>]+>", "", name).replace("i.c.", "").strip()
        out.append({"name": nm, "v1": float(v1), "v2": float(v2), "T": float(T), "Tstar": float(Ts)})
    return out


def match_catalog(orbit, catalog, tol=2e-5):
    """Same orbit if the starting velocities match, or — since one orbit passes through several collinear
    configurations, each a rescaled starting point — if the scale-invariant period T* = T·|E|^(3/2) matches
    (the catalogue rounds T* to 3 decimals), or is a k-fold repetition of a catalogued T*."""
    ts = orbit.get("Tstar")
    if ts is not None:
        for c in catalog:
            if abs(c["Tstar"] - ts) <= 0.0015:
                return c["name"] + (" (same orbit, different starting point)"
                                    if abs(c["v1"] - orbit["v1"]) > tol else "")
        for c in catalog:
            for k in (2, 3, 4, 5, 6):
                if abs(k * c["Tstar"] - ts) <= 0.0015 * k:
                    return f"{c['name']} repeated {k}×"
    for c in catalog:
        if abs(c["v1"] - orbit["v1"]) < tol and abs(c["v2"] - orbit["v2"]) < tol:
            for k in (1, 2, 3, 4, 5, 6):
                if abs(orbit["T"] - k * c["T"]) < 1e-4 * c["T"] * k or abs(c["T"] - k * orbit["T"]) < 1e-4 * c["T"]:
                    return c["name"]
    return None


# ------------------------------------------------------------- screening
def _acc(P):
    """P: (N, 3, 2) positions → accelerations (G = m = 1)."""
    a = np.zeros_like(P)
    for i in range(3):
        for j in range(3):
            if i != j:
                d = P[:, j] - P[:, i]
                r3 = (np.einsum("nk,nk->n", d, d) + 1e-12) ** 1.5
                a[:, i] += d / r3[:, None]
    return a


def screen(n_grid=300, T_max=40.0, dt=2e-3, log=print):
    """Vectorised Yoshida-4 integration of every bound (v₁, v₂) on an n×n grid; returns closest returns."""
    g = np.linspace(0.0, 1.0, n_grid + 2)[1:-1]
    V1, V2 = np.meshgrid(g, g, indexing="ij")
    V1, V2 = V1.ravel(), V2.ravel()
    bound = energy(V1, V2) < -0.05
    V1, V2 = V1[bound], V2[bound]
    N = len(V1)
    P = np.tile(X0.reshape(3, 2), (N, 1, 1))
    V = np.stack([np.stack([V1, V2], 1), np.stack([V1, V2], 1), np.stack([-2 * V1, -2 * V2], 1)], 1)
    Z0 = np.concatenate([P.reshape(N, 6), V.reshape(N, 6)], 1)
    w1 = 1 / (2 - 2 ** (1 / 3))
    w0 = 1 - 2 * w1
    cs = [w1 / 2, (w0 + w1) / 2, (w0 + w1) / 2, w1 / 2]
    ds = [w1, w0, w1]
    best_d = np.full(N, np.inf)
    best_t = np.zeros(N)
    alive = np.ones(N, bool)
    steps = int(T_max / dt)
    t0 = time.time()
    for s in range(1, steps + 1):
        for k in range(3):
            P += cs[k] * dt * V
            V += ds[k] * dt * _acc(P)
        P += cs[3] * dt * V
        if s % 5 == 0:
            t = s * dt
            Z = np.concatenate([P.reshape(N, 6), V.reshape(N, 6)], 1)
            d = np.sqrt(((Z - Z0) ** 2).sum(1))
            alive &= np.abs(P).max(axis=(1, 2)) < 50
            upd = alive & (t > 1.0) & (d < best_d)
            best_d[upd], best_t[upd] = d[upd], t
        if s % (steps // 10) == 0:
            log(f"    t = {s * dt:5.1f}/{T_max}  ({time.time() - t0:.0f}s)")
    order = np.argsort(best_d)
    return [(float(V1[i]), float(V2[i]), float(best_t[i]), float(best_d[i])) for i in order if best_d[i] < 0.25]


# --------------------------------------------------------------- refine
def _rhs(t, z):
    p = z[:6].reshape(3, 2)
    a = np.zeros((3, 2))
    for i in range(3):
        for j in range(3):
            if i != j:
                d = p[j] - p[i]
                a[i] += d / (d @ d) ** 1.5
    return np.concatenate([z[6:], a.ravel()])


def flow(v1, v2, T, tol=1e-12):
    sol = solve_ivp(_rhs, (0, T), initial_state(v1, v2), method="DOP853", rtol=tol, atol=tol)
    return sol.y[:, -1]


def refine(cand):
    v1, v2, T, d = cand
    if T < 1.5:
        return None

    def res(x):
        try:
            return flow(x[0], x[1], x[2], 1e-11) - initial_state(x[0], x[1])
        except Exception:
            return np.full(12, 1e3)
    try:
        r = least_squares(res, [v1, v2, T], xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=60)
    except Exception:
        return None
    v1, v2, T = r.x
    if not (0 < v1 < 1 and 0 < v2 < 1 and T > 1.5) or energy(v1, v2) >= 0:
        return None
    err = float(np.linalg.norm(flow(v1, v2, T, 1e-13) - initial_state(v1, v2)))
    if err > 1e-8:
        return None
    E = energy(v1, v2)
    return {"v1": float(v1), "v2": float(v2), "T": float(T), "Tstar": float(T * abs(E) ** 1.5),
            "closure_error": err}


def trajectory(o, n=1200):
    sol = solve_ivp(_rhs, (0, o["T"]), initial_state(o["v1"], o["v2"]), method="DOP853", rtol=1e-11,
                    atol=1e-11, t_eval=np.linspace(0, o["T"], n))
    return np.round(sol.y[:6].T, 4).tolist()


def run(n_grid=300, T_max=40.0, max_refine=400, log=print, space=None):
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog()
    log(f"Li & Liao catalogue: {len(catalog)} published equal-mass periodic orbits")
    log(f"1. screening a {n_grid}×{n_grid} grid of starting velocities (motions up to t = {T_max})…")
    cands = screen(n_grid, T_max, log=log)
    log(f"   {len(cands)} motions return close to their start")
    log(f"2. refining the best {min(max_refine, len(cands))} to closure < 1e-8…")
    with mp.Pool(4) as pool:
        refined = [r for r in pool.map(refine, cands[:max_refine]) if r]
    orbits = []
    for o in sorted(refined, key=lambda o: o["T"]):
        dup = next((x for x in orbits if abs(x["v1"] - o["v1"]) < 1e-6 and abs(x["v2"] - o["v2"]) < 1e-6), None)
        if dup:
            continue
        o["catalog"] = match_catalog(o, catalog)
        orbits.append(o)
    known = [o for o in orbits if o["catalog"]]
    new = [o for o in orbits if not o["catalog"]]
    log(f"3. {len(orbits)} distinct periodic orbits confirmed: {len(known)} in the published catalogue, "
        f"{len(new)} not found in it")
    for o in orbits:
        tag = o["catalog"] or "★ NOT IN CATALOGUE"
        log(f"   v1={o['v1']:.10f} v2={o['v2']:.10f} T={o['T']:.6f} T*={o['Tstar']:.3f} "
            f"closure={o['closure_error']:.1e}  {tag}")
    for o in orbits:
        o["trajectory"] = trajectory(o)
    (OUT / "orbits.json").write_text(json.dumps({"catalog_size": len(catalog), "grid": n_grid, "T_max": T_max,
                                                "orbits": orbits}))
    if space is not None:
        did = space.add("data", "Live model: Newtonian three-body gravity", domain="gravitation",
                        body=f"Grid {n_grid}², motions to t = {T_max}.", status="simulation", score=1.0,
                        key="model|threebody")
        for o in orbits:
            space.add("data_discovery" if o["catalog"] else "conjecture",
                      f"Periodic three-body orbit {o['catalog'] or '(not in catalogue)'}",
                      body=f"v1 = {o['v1']:.10f}, v2 = {o['v2']:.10f}, T = {o['T']:.6f}; closes to {o['closure_error']:.1e}.",
                      domain="gravitation", parents=[did],
                      status="rediscovered (Li & Liao catalogue)" if o["catalog"] else "not in the published catalogue",
                      score=1.0, key=f"orbit|{o['v1']:.8f}|{o['v2']:.8f}")
    return orbits, catalog


def screened_count(n_grid):
    g = np.linspace(0.0, 1.0, n_grid + 2)[1:-1]
    V1, V2 = np.meshgrid(g, g, indexing="ij")
    return int((energy(V1, V2) < -0.05).sum())


def export_lab(points=480):
    """Write the interactive Orbit Lab page (space/orbit_lab.html) from the exploration results."""
    d = json.loads((OUT / "orbits.json").read_text())
    for o in d["orbits"]:
        tr = o["trajectory"]
        step = max(1, len(tr) // points)
        o["trajectory"] = [[round(x, 3) for x in r] for r in tr[::step]] + [tr[0]]
    d["screened"] = screened_count(d["grid"])
    tpl = (Path(__file__).parent / "templates" / "orbit_lab.html").read_text()
    out = ROOT / "space" / "orbit_lab.html"
    out.write_text(tpl.replace("/*__DATA__*/null", json.dumps(d)))
    return out
