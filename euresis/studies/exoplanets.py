"""Study: the radius anomaly of hot Jupiters — an open problem, on real data.

Many giant planets orbiting close to their stars are larger than standard
cooling models allow. The extra heat is clearly tied to stellar irradiation,
but the mechanism (ohmic dissipation, tidal heating, delayed cooling, …) and
the exact law are unsettled.

Data: the Open Exoplanet Catalogue (real measurements, community-maintained,
https://github.com/OpenExoplanetCatalogue/oec_tables).

Steps
1. Validation — recover Kepler's third law from the catalogue's orbits.
2. Discovery — search Euresis' library of functional forms for the law linking
   planet radius to incident stellar flux and planet mass; rank every form by
   10-fold cross-validated error and BIC, alongside published-style power laws.
3. Residuals — test what the best law leaves unexplained (equilibrium
   temperature turnover, metallicity, age).
"""
from __future__ import annotations

import csv
import math
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "external" / "oec.csv"
URL = "https://raw.githubusercontent.com/OpenExoplanetCatalogue/oec_tables/master/comma_separated/open_exoplanet_catalogue.txt"
OUT = ROOT / "space" / "studies"

AU, RSUN, MSUN, DAY = 1.495_978_707e11, 6.957e8, 1.988_47e30, 86_400.0
SIGMA, G, S_EARTH = 5.670_374_419e-8, 6.674_30e-11, 1361.0


def load():
    if not DATA.exists():
        DATA.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, DATA)
    rows = [r for r in csv.DictReader(open(DATA)) if r["list"].startswith("Confirmed")]

    def f(r, k):
        try:
            v = float(r[k])
            return v if math.isfinite(v) else None
        except (TypeError, ValueError):
            return None
    return rows, f


# ---------------------------------------------------------------- validation
def validate_kepler(rows, f, log=print):
    from ..discover import DataDiscoverer, Dataset
    from ..engine import Engine
    from ..kb import KnowledgeBase
    pts = [(f(r, "semimajoraxis") * AU, f(r, "hoststar_mass") * MSUN, f(r, "period") * DAY)
           for r in rows if all(f(r, k) for k in ("semimajoraxis", "hoststar_mass", "period"))]
    # robust cleaning: iterative 3σ clipping around a free power-law fit (catalogue entries contain errors)
    A = np.array(pts)
    keep = np.ones(len(A), bool)
    for _ in range(5):
        X = np.vstack([np.ones(keep.sum()), np.log(A[keep, 0]), np.log(A[keep, 1])]).T
        c, *_ = np.linalg.lstsq(X, np.log(A[keep, 2]), rcond=None)
        res = np.log(A[:, 2]) - np.vstack([np.ones(len(A)), np.log(A[:, 0]), np.log(A[:, 1])]).T @ c
        sd = 1.4826 * np.median(np.abs(res[keep] - np.median(res[keep])))
        keep = np.abs(res) < 3 * sd
    log(f"   robust clipping kept {keep.sum()} of {len(A)} orbits ({len(A) - keep.sum()} catalogue outliers removed)")
    a, M, T = map(list, A[keep].T)
    kb = KnowledgeBase()
    dd = DataDiscoverer(kb, Engine(kb), log=log)
    ds = Dataset("oec_orbits", "Exoplanet orbits (Open Exoplanet Catalogue)", "Open Exoplanet Catalogue",
                 {"a": "semi_major_axis", "M": "mass", "T": "period"}, {"a": a, "M": M, "T": T}, "T", ["G"])
    return dd.run(ds), len(pts)


# ------------------------------------------------------------------ sample
def giant_sample(rows, f):
    out = []
    for r in rows:
        Mp, Rp, Ts, Rs = f(r, "mass"), f(r, "radius"), f(r, "hoststar_temperature"), f(r, "hoststar_radius")
        if None in (Mp, Rp, Ts, Rs) or not (0.3 <= Mp <= 13):
            continue
        a = f(r, "semimajoraxis")
        if a is None and f(r, "period") and f(r, "hoststar_mass"):
            P, Ms = f(r, "period") * DAY, f(r, "hoststar_mass") * MSUN
            a = (G * Ms * P ** 2 / (4 * math.pi ** 2)) ** (1 / 3) / AU
        if not a:
            continue
        flux = SIGMA * Ts ** 4 * (Rs * RSUN / (a * AU)) ** 2 / S_EARTH            # in Earth units
        teq = Ts * math.sqrt(Rs * RSUN / (2 * a * AU))
        out.append({"name": r["name"], "M": Mp, "R": Rp, "F": flux, "Teq": teq,
                    "FeH": f(r, "hoststar_metallicity"), "age": f(r, "hoststar_age") or f(r, "age")})
    return out


# ---------------------------------------------------------- model search
def model_search(F, M, R, folds=10, seed=0):
    """Rank every functional family (in flux, with a power-law mass factor) by CV error and BIC."""
    from scipy.optimize import least_squares
    from ..sr import families
    rng = np.random.default_rng(seed)
    n = len(R)
    fold = rng.permutation(n) % folds
    y = np.log(R)
    results = []

    def evaluate(name, k, predict_fn, fit_fn):
        cv = []
        for i in range(folds):
            tr, te = fold != i, fold == i
            th = fit_fn(tr)
            if th is None:
                return
            cv.append(np.mean((np.log(np.abs(predict_fn(th, te))) - y[te]) ** 2))
        th = fit_fn(np.ones(n, bool))
        if th is None:
            return
        resid = np.log(np.abs(predict_fn(th, np.ones(n, bool)))) - y
        rss = float(np.sum(resid ** 2))
        results.append({"model": name, "k": k, "cv_rmse_dex": math.sqrt(np.mean(cv)) / math.log(10),
                        "rms_dex": math.sqrt(rss / n) / math.log(10), "bic": n * math.log(rss / n) + k * math.log(n),
                        "params": [float(x) for x in th]})

    # baselines
    evaluate("constant radius", 1, lambda th, m: np.full(m.sum(), math.exp(th[0])),
             lambda m: np.array([y[m].mean()]))
    X = np.vstack([np.ones(n), np.log(M), np.log(F)]).T
    evaluate("power law  R = C·M^a·F^b  (Weiss et al. 2013 form)", 3,
             lambda th, m: np.exp(X[m] @ th), lambda m: np.linalg.lstsq(X[m], y[m], rcond=None)[0])
    X2 = np.vstack([np.ones(n), np.log(M), np.log(M) ** 2, np.log(F), np.log(F) ** 2]).T
    evaluate("quadratic in log M and log F", 5, lambda th, m: np.exp(X2[m] @ th),
             lambda m: np.linalg.lstsq(X2[m], y[m], rcond=None)[0])
    # Euresis family library: g(F) × M^c, fitted in log space
    for fam in families():
        def fit(mask, fam=fam):
            best = None
            for init in fam.inits[:10]:
                th0 = np.array(list(init) + [0.0], float)
                try:
                    r = least_squares(lambda th: np.log(np.abs(fam.f(F[mask], *th[:-1]) * M[mask] ** th[-1]) + 1e-300) - y[mask],
                                      th0, method="lm", max_nfev=4000)
                except (ValueError, FloatingPointError):
                    continue
                if np.all(np.isfinite(r.fun)) and (best is None or r.cost < best[0]):
                    best = (r.cost, r.x)
            return None if best is None else best[1]
        evaluate(f"Euresis: R = [{fam.name}](F) · M^c", fam.n_params + 1,
                 lambda th, m, fam=fam: fam.f(F[m], *th[:-1]) * M[m] ** th[-1], fit)
    results.sort(key=lambda r: r["bic"])
    return results


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


# -------------------------------------------------------------------- run
def run(log=print, plots=True):
    OUT.mkdir(parents=True, exist_ok=True)
    rows, f = load()
    log(f"Open Exoplanet Catalogue: {len(rows)} confirmed planets")
    log("\n1. Validation — Kepler's third law from the catalogue")
    kep, n_orb = validate_kepler(rows, f, log=lambda *a: log("  ", *a))
    S = giant_sample(rows, f)
    F = np.array([s["F"] for s in S]); M = np.array([s["M"] for s in S]); R = np.array([s["R"] for s in S])
    Teq = np.array([s["Teq"] for s in S])
    log(f"\n2. Hot-Jupiter radius anomaly — {len(S)} giant planets (0.3–13 M_J) with mass, radius and host star")
    res = model_search(F, M, R)
    for r in res[:8]:
        log(f"  BIC {r['bic']:8.1f}  CV {r['cv_rmse_dex']:.4f} dex  k={r['k']}  {r['model']}")
    best = res[0]
    base = next(r for r in res if r["model"].startswith("constant"))
    pw = next(r for r in res if r["model"].startswith("power law"))
    # residuals of the best model
    from ..sr import families
    fam = next((x for x in families() if f"[{x.name}]" in best["model"]), None)
    if fam is not None:
        th = np.array(best["params"])
        pred = fam.f(F, *th[:-1]) * M ** th[-1]
    else:
        X = np.vstack([np.ones(len(R)), np.log(M), np.log(F)]).T
        pred = np.exp(X @ np.array(pw["params"]))
    resid = np.log10(R / pred)
    log("\n3. What the best law leaves unexplained (Spearman rank correlation of residuals)")
    extras = {}
    for key in ("FeH", "age"):
        v = np.array([s[key] if s[key] is not None else np.nan for s in S])
        ok = np.isfinite(v)
        if ok.sum() > 30:
            extras[key] = (spearman(resid[ok], v[ok]), int(ok.sum()))
            log(f"  residual vs {key:4s}: ρ = {extras[key][0]:+.3f}  (n = {extras[key][1]})")
    extras["Teq"] = (spearman(resid, Teq), len(R))
    log(f"  residual vs Teq : ρ = {extras['Teq'][0]:+.3f}  (n = {len(R)})")
    if plots:
        _plots(F, M, R, Teq, pred, resid, best)
    report = _report(rows, n_orb, kep, S, res, best, base, pw, extras)
    (OUT / "hot_jupiters.md").write_text(report)
    log(f"\nreport: space/studies/hot_jupiters.md")
    return res, extras


def _plots(F, M, R, Teq, pred, resid, best):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, muted, grid, surf = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    series = [("0.3–1 M_J", (M < 1), "#2a78d6", "o"), ("1–3 M_J", (M >= 1) & (M < 3), "#eb6834", "s"),
              ("3–13 M_J", M >= 3, "#1baf7a", "^")]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": grid,
                         "axes.labelcolor": muted, "xtick.color": muted, "ytick.color": muted})
    fig, ax = plt.subplots(figsize=(8, 5), dpi=160, facecolor=surf)
    ax.set_facecolor(surf)
    for lab, msk, col, mk in series:
        ax.scatter(F[msk], R[msk], s=22, c=col, marker=mk, edgecolors=surf, linewidths=0.6, label=lab, zorder=3)
    order = np.argsort(F)
    for lab, msk, col, mk in series:
        Mm = np.median(M[msk])
        xs = np.logspace(np.log10(F.min()), np.log10(F.max()), 200)
        from ..sr import families
        fam = next((x for x in families() if f"[{x.name}]" in best["model"]), None)
        if fam is not None:
            th = np.array(best["params"])
            ax.plot(xs, fam.f(xs, *th[:-1]) * Mm ** th[-1], color=col, lw=2, zorder=4)
    ax.set_xscale("log")
    ax.set_xlabel("Incident stellar flux (Earth = 1)")
    ax.set_ylabel("Planet radius (Jupiter radii)")
    ax.set_title("Giant exoplanets grow with irradiation — best law found by Euresis", color=ink, loc="left", fontsize=11)
    ax.grid(color=grid, lw=0.6, zorder=0)
    ax.legend(title="Planet mass (lines: law at median mass)", frameon=False, fontsize=9, title_fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "hot_jupiters_radius_vs_flux.png", facecolor=surf)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4), dpi=160, facecolor=surf)
    ax.set_facecolor(surf)
    ax.axhline(0, color=muted, lw=1, zorder=2)
    for lab, msk, col, mk in series:
        ax.scatter(Teq[msk], resid[msk], s=20, c=col, marker=mk, edgecolors=surf, linewidths=0.6, label=lab, zorder=3)
    bins = np.linspace(Teq.min(), Teq.max(), 12)
    idx = np.digitize(Teq, bins)
    med = [(np.median(Teq[idx == i]), np.median(resid[idx == i])) for i in range(1, len(bins)) if (idx == i).sum() >= 8]
    if med:
        ax.plot(*zip(*med), color=ink, lw=2, zorder=4, label="running median")
    ax.set_xlabel("Equilibrium temperature (K)")
    ax.set_ylabel("Radius residual (dex)")
    ax.set_title("What the law leaves unexplained", color=ink, loc="left", fontsize=11)
    ax.grid(color=grid, lw=0.6, zorder=0)
    ax.legend(frameon=False, fontsize=9, ncol=4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "hot_jupiters_residuals.png", facecolor=surf)
    plt.close(fig)


def _report(rows, n_orb, kep, S, res, best, base, pw, extras):
    L = ["# Euresis study: the hot-Jupiter radius anomaly", "",
         f"Data: Open Exoplanet Catalogue, {len(rows)} confirmed planets (downloaded from GitHub).", "",
         "## 1. Validation", "", f"From {n_orb} planetary orbits:", ""]
    L += [f"- {l}" for l in kep["lines"]]
    L += ["", "Caveat: catalogues often *derive* semi-major axes from the period and stellar mass via Kepler's "
          "law, so this check validates the pipeline on real catalogue data rather than testing Kepler's law "
          "independently.", "",
          "## 2. Radius versus irradiation and mass", "",
          f"{len(S)} giant planets (0.3–13 Jupiter masses) with measured mass and radius. "
          "Every model below was fitted in log-radius and scored by 10-fold cross-validation (CV) and BIC "
          "(lower is better).", "",
          "| Rank | Model | Params | CV error (dex) | BIC |", "|---|---|---|---|---|"]
    for i, r in enumerate(res[:10], 1):
        L.append(f"| {i} | {r['model']} | {r['k']} | {r['cv_rmse_dex']:.4f} | {r['bic']:.1f} |")
    L += ["", f"**Best law (by BIC): {best['model']}**, parameters "
          f"{', '.join(f'{p:.4g}' for p in best['params'])}.", "",
          f"It explains the data with a CV error of {best['cv_rmse_dex']:.4f} dex, versus "
          f"{pw['cv_rmse_dex']:.4f} dex for the published-style power law and {base['cv_rmse_dex']:.4f} dex "
          f"for a constant radius.", "",
          "## 3. Residuals", ""]
    for k, (rho, n) in extras.items():
        L.append(f"- residual vs {k}: Spearman ρ = {rho:+.3f} (n = {n})")
    L += ["", "## Honest assessment", "",
          "* Published empirical relations exist for this anomaly. For example, Weiss et al. (2013) give "
          "R ∝ M^−0.04 F^0.094 for giant planets, and Thorngren & Fortney (2018) infer a heating efficiency "
          "that peaks near Teq ≈ 1500 K. These are cited from memory: the literature search could not run in "
          "this environment, so the novelty of any result here is **unchecked**.",
          "* A better-fitting functional form on one catalogue is a *candidate* empirical law, not a "
          "discovery. To become one it must hold on independent, homogeneous data (for example, the NASA "
          "Exoplanet Archive with uniform stellar parameters), be compared against the literature, and "
          "ideally be explained physically.", ""]
    return "\n".join(L)
