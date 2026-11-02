"""Data-driven discovery: find laws in measurements.

Given a table of measurements, Euresis

1. searches for the functional form (power laws, exponentials, reciprocals,
   inverse squares…) that best fits the target, using the data alone;
2. checks the result against dimensional analysis — the exponents the data
   prefers must be the ones the units allow;
3. compares fitted constants with known constants and tries to *explain*
   any residual mismatch with combinations of known dimensionless numbers
   (this is how a small, real discrepancy can point at new physics);
4. tests whether the law is already in its knowledge base and records the
   whole chain — data → form → constant → interpretation — in the Thought Space.

Embedded datasets are real measurements (sources given). Use your own data with
``python -m euresis discover --csv file.csv --target col --map col:quantity ...``.
"""
from __future__ import annotations

import csv
import itertools
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import sympy as sp

from .engine import Engine, Relation
from .kb import KnowledgeBase

AU = 1.495_978_707e11
DAY = 86_400.0
M_SUN, M_JUP, M_EARTH = 1.988_47e30, 1.898_13e27, 5.972_17e24


@dataclass
class Dataset:
    name: str
    description: str
    source: str
    columns: dict            # column -> quantity id
    data: dict               # column -> list of SI values
    target: str
    constants: list = field(default_factory=list)   # constants that may enter the law
    integer_cols: tuple = ()                          # columns that are integers (quantum numbers…)


def builtin() -> list[Dataset]:
    planets = [  # semi-major axis (AU), sidereal period (days)
        ("Mercury", 0.387_098, 87.969), ("Venus", 0.723_332, 224.701), ("Earth", 1.000_001, 365.256),
        ("Mars", 1.523_679, 686.980), ("Jupiter", 5.2044, 4_332.589), ("Saturn", 9.5826, 10_759.22),
        ("Uranus", 19.2184, 30_685.4), ("Neptune", 30.110, 60_189.0)]
    moons = [  # Galilean moons: a (km), period (days)
        ("Io", 421_700, 1.769_138), ("Europa", 671_034, 3.551_181),
        ("Ganymede", 1_070_412, 7.154_553), ("Callisto", 1_882_709, 16.689_017)]
    earth_orbits = [("Moon", 384_400, 27.321_661), ("GPS", 26_560, 0.498_6), ("Geostationary", 42_164, 0.997_27)]
    a, T, M = [], [], []
    for _, au, d in planets:
        a.append(au * AU); T.append(d * DAY); M.append(M_SUN)
    for _, km, d in moons:
        a.append(km * 1e3); T.append(d * DAY); M.append(M_JUP)
    for _, km, d in earth_orbits:
        a.append(km * 1e3); T.append(d * DAY); M.append(M_EARTH)
    orbits = Dataset(
        "orbits", "Orbits around the Sun, Jupiter and Earth: semi-major axis, period, central mass",
        "NASA planetary & satellite fact sheets; GPS and geostationary orbit specifications",
        {"a": "semi_major_axis", "T": "period", "M": "mass"}, {"a": a, "T": T, "M": M}, "T", ["G"])

    # Hydrogen Balmer series, vacuum wavelengths (nm), upper level n -> 2
    balmer_nm = {3: 656.461, 4: 486.271, 5: 434.170, 6: 410.292, 7: 397.123, 8: 389.017}
    balmer = Dataset(
        "balmer", "Hydrogen Balmer emission lines: upper quantum number n, vacuum wavelength",
        "NIST Atomic Spectra Database (vacuum wavelengths)",
        {"n": "quantum_number", "lam": "wavelength"},
        {"n": list(balmer_nm), "lam": [v * 1e-9 for v in balmer_nm.values()]}, "lam", [], ("n",))

    # U.S. Standard Atmosphere 1976: geopotential altitude (m), pressure (Pa)
    atm = [(0, 101_325), (1_000, 89_876), (2_000, 79_501), (3_000, 70_121), (5_000, 54_048),
           (8_000, 35_651), (10_000, 26_500), (15_000, 12_111), (20_000, 5_529), (25_000, 2_549),
           (30_000, 1_197)]
    atmosphere = Dataset(
        "atmosphere", "Air pressure versus altitude", "U.S. Standard Atmosphere, 1976",
        {"h": "height", "P": "pressure"}, {"h": [x for x, _ in atm], "P": [y for _, y in atm]}, "P")
    return [orbits, balmer, atmosphere]


def load_csv(path, target, mapping: dict[str, str], name=None) -> Dataset:
    rows = list(csv.DictReader(open(path)))
    data = {c: [float(r[c]) for r in rows] for c in mapping}
    return Dataset(name or Path(path).stem, f"user data from {Path(path).name}", str(path),
                   mapping, data, target)


# ----------------------------------------------------------------- form search
UNARY = {
    "x": (lambda x: x, "{x}"), "1/x": (lambda x: 1 / x, "1/{x}"), "x^2": (lambda x: x ** 2, "{x}^2"),
    "1/x^2": (lambda x: 1 / x ** 2, "1/{x}^2"), "sqrt(x)": (np.sqrt, "√{x}"), "log(x)": (np.log, "ln {x}"),
}
TARGET_T = {
    "y": (lambda y: y, lambda t: t), "1/y": (lambda y: 1 / y, lambda t: 1 / t),
    "log(y)": (np.log, np.exp), "y^2": (lambda y: y ** 2, np.sqrt),
}


def _rational(v, max_den=6, tol=0.02):
    best = None
    for d in range(1, max_den + 1):
        n = round(v * d)
        err = abs(v - n / d)
        if err <= tol and (best is None or err < best[0] - 1e-12):
            best = (err, sp.Rational(n, d))
    return best[1] if best else None


def search_forms(ds: Dataset):
    """Try every transform pair T(y) = A + B·f(x) (one input) and a multivariate power law."""
    y = np.array(ds.data[ds.target], float)
    inputs = [c for c in ds.columns if c != ds.target]
    out = []
    for c in inputs:
        x = np.array(ds.data[c], float)
        for (tn, (tf, tinv)), (fn, (ff, ftxt)) in itertools.product(TARGET_T.items(), UNARY.items()):
            with np.errstate(all="ignore"):
                Ty, fx = tf(y), ff(x)
            if not (np.all(np.isfinite(Ty)) and np.all(np.isfinite(fx))) or np.ptp(fx) == 0:
                continue
            Am = np.vstack([np.ones_like(fx), fx]).T
            try:
                (A, B), *_ = np.linalg.lstsq(Am, Ty, rcond=None)
            except np.linalg.LinAlgError:
                continue
            with np.errstate(all="ignore"):
                pred = tinv(A + B * fx)
            rel = np.abs(pred - y) / np.abs(y)
            if not np.all(np.isfinite(rel)):
                continue
            out.append({"kind": "transform", "T": tn, "f": fn, "x": c, "A": A, "B": B,
                        "max_err": float(rel.max()), "rms_err": float(np.sqrt(np.mean(rel ** 2)))})
    # multivariate power law  y = C · Π x_i^a_i
    pos = [c for c in inputs if np.all(np.array(ds.data[c], float) > 0)]
    X = np.array([np.log(np.array(ds.data[c], float)) for c in pos]).T if pos else np.zeros((len(y), 0))
    keep = [i for i in range(X.shape[1]) if np.ptp(X[:, i]) > 0]
    inputs = pos
    if keep and np.all(y > 0):
        Xk = np.hstack([np.ones((len(y), 1)), X[:, keep]])
        coef, *_ = np.linalg.lstsq(Xk, np.log(y), rcond=None)
        pred = np.exp(Xk @ coef)
        rel = np.abs(pred - y) / y
        out.append({"kind": "power", "inputs": [inputs[i] for i in keep], "logC": coef[0],
                    "exps": list(coef[1:]), "max_err": float(rel.max()),
                    "rms_err": float(np.sqrt(np.mean(rel ** 2)))})
    out.sort(key=lambda r: r["rms_err"] + 0.002 * (r["kind"] == "transform" and r["T"] != "y"))
    return out


class DataDiscoverer:
    def __init__(self, kb: KnowledgeBase, engine: Engine, space=None, log=print):
        self.kb, self.E, self.space, self.log = kb, engine, space, log
        self.findings: list[dict] = []

    def _add(self, *a, **kw):
        return self.space.add(*a, **kw) if self.space is not None else None

    def _law_ids(self, names):
        if self.space is None:
            return []
        out = []
        for n in names:
            tid = self.space.make_id("law", f"law|{n}")
            if tid in self.space.thoughts:
                out.append(tid)
        return out

    # ------------------------------------------------------- interpretation
    def explain_ratio(self, r: float, tol=0.15):
        """Explain a fitted/known ratio close to 1 by small known dimensionless numbers."""
        c = self.kb.constants
        smalls = {"m_e/m_p": c["m_e"][1] / c["m_p"][1], "α": c["alpha"][1], "α²": c["alpha"][1] ** 2,
                  "m_e/m_n": c["m_e"][1] / c["m_n"][1], "m_e/m_μ": c["m_e"][1] / c["m_mu"][1]}
        dev = r - 1
        best = None
        for name, s in smalls.items():
            for form, val in ((f"1/(1 + {name})", 1 / (1 + s) - 1), (f"1 + {name}", s), (f"1 - {name}", -s),
                              (f"1 + {name}/2", s / 2), (f"1 - {name}/2", -s / 2)):
                if dev == 0 or val == 0:
                    continue
                q = abs(dev - val) / abs(val)
                if q < tol and (best is None or q < 0.9 * best[2]):
                    best = (form, val, q)
        return best

    def match_constant(self, value: float, dim) -> list[tuple[str, sp.Expr, float]]:
        hits = []
        for k, (name, v, unit, dspec, _) in self.kb.constants.items():
            from .dimensions import D
            if D(dspec) != dim or v == 0:
                continue
            g = sp.nsimplify(value / v, [sp.pi], tolerance=1e-3)
            if len(str(g)) <= 8:
                hits.append((k, g, value / (float(g) * v)))
        return hits

    # --------------------------------------------------------------- driver
    def run(self, ds: Dataset):
        self.log(f"dataset '{ds.name}': {ds.description} ({len(ds.data[ds.target])} measurements)")
        did = self._add("data", f"Data: {ds.description}", body=f"Source: {ds.source}. "
                        f"{len(ds.data[ds.target])} measurements.", domain="method",
                        status="measured data", score=0.8, key=f"data|{ds.name}")
        forms = search_forms(ds)
        if not forms:
            self.log("  no form fits")
            return None
        best = forms[0]
        tq = ds.columns[ds.target]
        finding = {"dataset": ds.name, "best": best, "alternatives": forms[1:4]}
        if best["kind"] == "power":
            finding.update(self._interpret_power(ds, best, did))
        else:
            finding.update(self._interpret_transform(ds, best, did))
        self.findings.append(finding)
        return finding

    def _interpret_power(self, ds, best, did):
        tq = ds.columns[ds.target]
        names = best["inputs"]
        exps = best["exps"]
        rat = [_rational(e) for e in exps]
        txt = " · ".join(f"{c}^{e:.4f}" for c, e in zip(names, exps))
        self.log(f"  data alone: {ds.target} ∝ {txt}   (rms error {best['rms_err'] * 100:.3f}%)")
        # dimensional analysis with the allowed constants
        syms = [sp.Symbol(ds.columns[c]) for c in names] + [sp.Symbol(k) for k in ds.constants]
        dexps, _ = self.E.rayleigh(self.kb.quantities[tq][1], syms)
        agree = dexps is not None and all(r is not None and r == d for r, d in zip(rat, dexps[:len(names)]))
        lines = [f"Fitting the data alone gives {ds.target} ∝ {txt} (rms error {best['rms_err'] * 100:.3f}%)."]
        status = "empirical law"
        rel = None
        if dexps is not None:
            mono = self.E.monomial(syms, dexps)
            # fit the dimensionless prefactor
            vals = []
            for i in range(len(ds.data[ds.target])):
                sub = {sp.Symbol(ds.columns[c]): ds.data[c][i] for c in names}
                sub.update({sp.Symbol(k): self.kb.constants[k][1] for k in ds.constants})
                vals.append(ds.data[ds.target][i] / float(mono.subs(sub)))
            C = float(np.mean(vals))
            spread = float(np.std(vals) / C)
            Cs = sp.nsimplify(C, [sp.pi], tolerance=2e-3 * C)
            lines.append(f"Dimensional analysis with {', '.join(ds.constants) or 'no constants'} requires exponents "
                         f"{[str(d) for d in dexps[:len(names)]]} — the data {'AGREE' if agree else 'DISAGREE'}.")
            lines.append(f"Prefactor from data: C = {C:.5g} (scatter {spread * 100:.3f}%)"
                         + (f" ≈ {Cs}" if len(str(Cs)) <= 8 else "") + ".")
            ts = sp.Symbol(tq)
            expr = (Cs if len(str(Cs)) <= 8 else sp.Float(C, 6)) * mono
            s2q = {sp.Symbol(ds.columns[c]): ds.columns[c] for c in names}
            s2q[ts] = tq
            rel = Relation(sp.Eq(ts, expr), s2q, {sp.Symbol(k) for k in ds.constants}, "data", [], "fitted from data", ts)
            status = "law recovered from data, dimensionally verified" if agree else "empirical law"
        return self._conclude(ds, did, rel, lines, status)

    def _interpret_transform(self, ds, best, did):
        tq = ds.columns[ds.target]
        x = best["x"]
        xq = ds.columns[x]
        A, B = best["A"], best["B"]
        lines = [f"Best form found in the data: {best['T'].replace('y', ds.target)} = A + B·"
                 f"{best['f'].replace('x', x)}, with A = {A:.6g}, B = {B:.6g} "
                 f"(rms error {best['rms_err'] * 100:.4f}%)."]
        ts, xs = sp.Symbol(tq), sp.Symbol(xq)
        fexpr = {"x": xs, "1/x": 1 / xs, "x^2": xs ** 2, "1/x^2": 1 / xs ** 2, "sqrt(x)": sp.sqrt(xs),
                 "log(x)": sp.log(xs)}[best["f"]]
        rel, status = None, "empirical law"
        if best["T"] == "log(y)" and best["f"] == "x":
            # exponential law y = y0·exp(-x/L)
            y0, Lsc = math.exp(A), -1 / B
            lines.append(f"This is exponential decay: {ds.target} = {y0:.5g}·exp(−{x}/{Lsc:.5g}) — a characteristic "
                         f"scale of {Lsc:.4g} (SI units of {self.kb.qname(xq)}).")
            # connect to prior knowledge: which known law has this shape?
            Tm = None
            if tq == "pressure" and xq in ("height", "depth"):
                M, g = 0.028_964_4, self.kb.constants["g_n"][1]
                Tm = Lsc * M * g / self.kb.constants["R"][1]
                lines.append(f"Connecting to known laws (barometric formula + atmospheric scale height H = RT/(Mg)): "
                             f"the fitted scale height implies a mean air temperature of {Tm:.1f} K "
                             f"({Tm - 273.15:.1f} °C) over this altitude range.")
            rel = Relation(sp.Eq(ts, sp.Float(y0, 6) * sp.exp(-xs / sp.Float(Lsc, 6))), {ts: tq, xs: xq}, set(),
                           "data", [], "exponential law from data", ts)
            status = "exponential law found in data; connected to barometric formula"
        elif best["T"] == "1/y" and best["f"] == "1/x^2" and ds.integer_cols:
            # Rydberg-type series 1/λ = A − R/n²
            Rfit = -B
            m2 = A / Rfit
            m = _rational(math.sqrt(1 / m2), 1, 0.01) if m2 > 0 else None
            lines.append(f"Integer structure: 1/{ds.target} = {Rfit:.7g}·(1/{(1 / m2):.4f} − 1/{x}²); "
                         f"1/{(1 / m2):.4f} ≈ 1/{m}² — every line ends on level {m}.")
            hits = self.match_constant(Rfit, self.kb.quantities["wavenumber"][1])
            for k, g, r in hits:
                lines.append(f"Fitted constant = {g}×{self.kb.constants[k][0]} to within {abs(r - 1) * 100:.4f}%.")
                ex = self.explain_ratio(r)
                if ex and abs(r - 1) > 1e-5:
                    lines.append(f"The residual ratio {r:.7f} is explained by the factor {ex[0]} "
                                 f"(predicted {1 + ex[1]:.7f}): the nucleus is not infinitely heavy — "
                                 f"the electron orbits the centre of mass (reduced-mass correction).")
            if m is not None:
                rel = Relation(sp.Eq(1 / sp.Symbol("wavelength"),
                                     sp.Float(Rfit, 8) * (sp.Rational(1, int(m) ** 2) - 1 / xs ** 2)),
                               {sp.Symbol("wavelength"): "wavelength", xs: xq}, set(), "data", [], "series law", None)
            status = "spectral series law found in data; constant identified"
        else:
            rel = Relation(sp.Eq(ts, sp.Float(A, 6) + sp.Float(B, 6) * fexpr), {ts: tq, xs: xq}, set(), "data",
                           [], "fitted", ts)
        return self._conclude(ds, did, rel, lines, status)

    def _conclude(self, ds, did, rel, lines, status):
        known = None
        if rel is not None and rel.constants:
            k, ratio = self.E.find_known(rel)
            if k is not None:
                known = k.name
                lines.append(f"Matches the known law '{k.name}'" + ("" if ratio in (1, -1) else f" up to factor {ratio}") + ".")
        for l in lines:
            self.log("  " + l)
        title = (f"From data: {known}" if known else f"From data: {ds.description.split(':')[0]}")
        formula = self.E.pretty(rel) if rel is not None and isinstance(rel.eq, sp.Equality) else ""
        parents = [p for p in [did] if p] + self._law_ids([known] if known else [])
        if ds.name == "atmosphere":
            parents += self._law_ids(["Barometric formula", "Atmospheric scale height"])
        if ds.name == "balmer":
            parents += self._law_ids(["Rydberg formula", "Bohr energy levels of hydrogen", "Reduced mass"])
        if ds.name == "orbits":
            parents += self._law_ids(["Kepler's third law"])
        self._add("data_discovery", title, body=" ".join(lines), formula=formula, domain="method",
                  parents=parents, status=status, score=1.0, key=f"datadisc|{ds.name}")
        return {"lines": lines, "known": known, "status": status, "formula": formula}
