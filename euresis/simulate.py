"""Simulators — numerical experiments Euresis can run to test ideas.

All models integrate their governing equations numerically (SciPy's adaptive
Runge–Kutta), so they make no small-angle, low-speed or linear approximations
unless asked. Results are labelled *simulated*: they test whether an idea is
consistent with the underlying equations, not with nature.

physics   pendulum · orbit · projectile · oscillator · rlc · heat1d
chemistry kinetics (mass-action networks) · arrhenius
climate   ebm (zero-dimensional energy balance with ice–albedo feedback)
"""
from __future__ import annotations

import itertools
import math
import re

import numpy as np
from scipy.integrate import solve_ivp

G = 6.674_30e-11
SIGMA = 5.670_374_419e-8
R_GAS = 8.314_462_618


def _period_from_crossings(t, x):
    s = np.sign(x)
    idx = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    if len(idx) < 2:
        return None
    tc = [t[i] - x[i] * (t[i + 1] - t[i]) / (x[i + 1] - x[i]) for i in idx]
    return float(np.mean(np.diff(tc)))


# ---------------------------------------------------------------- physics
def pendulum(length=1.0, g=9.80665, theta0=0.1, damping=0.0, periods=20):
    """Full nonlinear pendulum θ'' = −(g/L) sin θ − bθ'. Returns measured period."""
    w0 = math.sqrt(g / length)
    t_end = periods * 2 * math.pi / w0
    sol = solve_ivp(lambda t, y: [y[1], -(g / length) * math.sin(y[0]) - damping * y[1]],
                    (0, t_end), [theta0, 0.0], max_step=t_end / (periods * 400), rtol=1e-10, atol=1e-12)
    T = _period_from_crossings(sol.t, sol.y[0] - 0.0) or _period_from_crossings(sol.t, sol.y[1])
    return {"period": T, "small_angle_period": 2 * math.pi / w0,
            "ratio_to_small_angle": T / (2 * math.pi / w0) if T else None}


def orbit(mass=1.988_47e30, r0=1.495_978_707e11, v_factor=1.0, orbits=3):
    """Two-body orbit around a fixed central mass. v_factor=1 → circular. Returns period, a, e."""
    v0 = v_factor * math.sqrt(G * mass / r0)
    a = 1 / (2 / r0 - v0 ** 2 / (G * mass))
    if a <= 0:
        return {"bound": False, "escape_speed": math.sqrt(2 * G * mass / r0)}
    T_guess = 2 * math.pi * math.sqrt(a ** 3 / (G * mass))

    def f(t, y):
        r3 = (y[0] ** 2 + y[1] ** 2) ** 1.5
        return [y[2], y[3], -G * mass * y[0] / r3, -G * mass * y[1] / r3]
    sol = solve_ivp(f, (0, orbits * T_guess), [r0, 0, 0, v0], rtol=1e-10, atol=1e-6 * r0,
                    max_step=T_guess / 500)
    T = _period_from_crossings(sol.t, sol.y[1])
    r = np.hypot(sol.y[0], sol.y[1])
    return {"bound": True, "period": T, "semi_major_axis": float((r.max() + r.min()) / 2),
            "eccentricity": float((r.max() - r.min()) / (r.max() + r.min()))}


def projectile(v0=50.0, angle_deg=45.0, g=9.80665, drag_per_mass=0.0, mass=1.0):
    """Projectile with quadratic drag (a_drag = −k|v|v). Returns range, max height, flight time."""
    th = math.radians(angle_deg)
    k = drag_per_mass

    def f(t, y):
        sp = math.hypot(y[2], y[3])
        return [y[2], y[3], -k * sp * y[2], -g - k * sp * y[3]]
    hit = lambda t, y: y[1]
    hit.terminal, hit.direction = True, -1
    sol = solve_ivp(f, (0, 10 * v0 / g + 1), [0, 0, v0 * math.cos(th), v0 * math.sin(th)], events=hit,
                    max_step=0.01 * v0 / g + 1e-3, rtol=1e-9)
    tf = float(sol.t_events[0][0]) if len(sol.t_events[0]) else float(sol.t[-1])
    return {"range": float(sol.y_events[0][0][0]) if len(sol.t_events[0]) else float(sol.y[0][-1]),
            "max_height": float(sol.y[1].max()), "flight_time": tf}


def oscillator(mass=1.0, k=10.0, damping=0.0, force=0.0, drive_freq=0.0, t_end=60.0):
    """m x'' + b x' + k x = F cos(ω t). Returns period and late-time amplitude."""
    sol = solve_ivp(lambda t, y: [y[1], (force * math.cos(drive_freq * t) - damping * y[1] - k * y[0]) / mass],
                    (0, t_end), [1.0 if force == 0 else 0.0, 0.0], max_step=t_end / 6000, rtol=1e-9)
    late = sol.t > 0.7 * t_end
    return {"period": _period_from_crossings(sol.t, sol.y[0]),
            "late_amplitude": float(np.abs(sol.y[0][late]).max()),
            "natural_period": 2 * math.pi * math.sqrt(mass / k)}


def rlc(R=10.0, L=1e-3, C=1e-6, V0=1.0, t_end=None):
    """Series RLC discharge: L q'' + R q' + q/C = 0, q(0) = C V0. Returns oscillation period, decay time."""
    t_end = t_end or 40 * math.sqrt(L * C) * 2 * math.pi
    sol = solve_ivp(lambda t, y: [y[1], -(R * y[1] + y[0] / C) / L], (0, t_end), [C * V0, 0.0],
                    max_step=t_end / 20000, rtol=1e-9, atol=1e-15)
    q = sol.y[0]
    env = np.abs(q) > np.abs(q[0]) / math.e
    decay = float(sol.t[np.where(env)[0][-1]]) if env.any() else None
    return {"period": _period_from_crossings(sol.t, q), "LC_period": 2 * math.pi * math.sqrt(L * C),
            "envelope_decay_time": decay, "2L/R": 2 * L / R}


def heat1d(length=1.0, diffusivity=1e-4, t_end=1000.0, n=101, T_left=100.0, T_right=0.0, T_init=0.0):
    """1-D heat equation by finite differences. Returns midpoint temperature and the profile."""
    dx = length / (n - 1)
    dt = 0.4 * dx * dx / diffusivity
    steps = int(t_end / dt) + 1
    T = np.full(n, T_init, float)
    T[0], T[-1] = T_left, T_right
    r = diffusivity * dt / dx / dx
    for _ in range(steps):
        T[1:-1] += r * (T[2:] - 2 * T[1:-1] + T[:-2])
    return {"midpoint_temperature": float(T[n // 2]), "profile": [round(float(x), 4) for x in T[:: max(1, n // 10)]],
            "diffusion_time_L2_over_D": length ** 2 / diffusivity}


# --------------------------------------------------------------- chemistry
def kinetics(reactions: list[str], rate_constants: list[float], initial: dict, t_end=100.0, points=11):
    """Mass-action kinetics for reactions like 'A + B -> C' or '2 A -> B'. Concentrations in mol/L."""
    species = sorted(set(initial) | {s for r in reactions for s in re.findall(r"[A-Za-z][A-Za-z0-9_]*", r)})
    idx = {s: i for i, s in enumerate(species)}

    def parse(side):
        out = []
        for term in side.split("+"):
            m = re.match(r"\s*(\d*)\s*([A-Za-z][A-Za-z0-9_]*)\s*$", term)
            if m:
                out.append((int(m.group(1) or 1), m.group(2)))
        return out
    rxns = [(parse(r.split("->")[0]), parse(r.split("->")[1])) for r in reactions]

    def f(t, c):
        d = np.zeros_like(c)
        for (lhs, rhs), k in zip(rxns, rate_constants):
            rate = k * math.prod(max(c[idx[s]], 0) ** n for n, s in lhs)
            for n, s in lhs:
                d[idx[s]] -= n * rate
            for n, s in rhs:
                d[idx[s]] += n * rate
        return d
    c0 = [initial.get(s, 0.0) for s in species]
    ts = np.linspace(0, t_end, points)
    sol = solve_ivp(f, (0, t_end), c0, t_eval=ts, method="LSODA", rtol=1e-9, atol=1e-12)
    return {"t": [float(x) for x in ts],
            **{s: [round(float(v), 8) for v in sol.y[i]] for s, i in idx.items()}}


def arrhenius(A=1e13, Ea=80e3, temperatures=(280, 300, 320, 340, 360)):
    """Rate constants over temperature; fitted activation energy from ln k vs 1/T."""
    T = np.array(temperatures, float)
    k = A * np.exp(-Ea / (R_GAS * T))
    slope = np.polyfit(1 / T, np.log(k), 1)[0]
    return {"T": T.tolist(), "k": k.tolist(), "fitted_Ea": float(-slope * R_GAS)}


# ----------------------------------------------------------------- climate
def ebm(co2_ppm=280.0, years=300, ice_albedo_feedback=True, ocean_depth=70.0, solar=1361.0, T0=288.0,
        emissivity=0.612, forcing_coefficient=5.35):
    """Zero-dimensional energy balance: C dT/dt = S(1−α(T))/4 − εσT⁴ + 5.35·ln(CO2/280).

    α(T) falls from 0.45 (icy) to 0.29 (ice-free) around 265 K when the ice–albedo feedback is on.
    A textbook toy model: it captures feedback structure, not regional climate."""
    Cheat = 1000 * 4186 * ocean_depth

    def albedo(T):
        return 0.37 - 0.08 * math.tanh((T - 265.0) / 10.0) if ice_albedo_feedback else 0.30

    def f(t, y):
        T = y[0]
        return [(solar * (1 - albedo(T)) / 4 - emissivity * SIGMA * T ** 4
                 + forcing_coefficient * math.log(co2_ppm / 280.0)) / Cheat]
    yr = 3.155_76e7
    sol = solve_ivp(f, (0, years * yr), [T0], t_eval=np.linspace(0, years * yr, 11), rtol=1e-9)
    base = solve_ivp(lambda t, y: [(solar * (1 - albedo(y[0])) / 4 - emissivity * SIGMA * y[0] ** 4) / Cheat],
                     (0, years * yr), [T0], rtol=1e-9)
    return {"years": [round(float(t / yr), 1) for t in sol.t], "temperature_K": [round(float(x), 3) for x in sol.y[0]],
            "baseline_equilibrium_K": round(float(base.y[0][-1]), 3),
            "warming_K": round(float(sol.y[0][-1] - base.y[0][-1]), 3)}


MODELS = {"pendulum": pendulum, "orbit": orbit, "projectile": projectile, "oscillator": oscillator,
          "rlc": rlc, "heat1d": heat1d, "kinetics": kinetics, "arrhenius": arrhenius, "ebm": ebm}


def run(model: str, **params):
    if model not in MODELS:
        raise ValueError(f"unknown model '{model}'. Available: {', '.join(MODELS)}")
    return MODELS[model](**params)


def experiment(model: str, vary: dict, measure: str, fixed: dict | None = None) -> dict:
    """Run a model over a grid of parameters → a dataset of (inputs…, measured output)."""
    keys = list(vary)
    rows = []
    for combo in itertools.product(*[vary[k] for k in keys]):
        params = dict(fixed or {}, **dict(zip(keys, combo)))
        out = run(model, **params)
        if out.get(measure) is not None:
            rows.append({**dict(zip(keys, combo)), measure: out[measure]})
    return {"columns": keys + [measure], "rows": rows}
