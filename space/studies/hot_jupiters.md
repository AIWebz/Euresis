# Euresis study: the hot-Jupiter radius anomaly

Data: Open Exoplanet Catalogue, 5287 confirmed planets (downloaded from GitHub).

## 1. Validation

From 2431 planetary orbits:

- Fitting the data alone gives T ∝ a^1.4999 · M^-0.4995 (rms error 0.221%).
- Dimensional analysis with G requires exponents ['3/2', '-1/2'] — the data AGREE.
- Prefactor from data: C = 6.2816 (scatter 0.223%) ≈ 2*pi.
- Matches the known law 'Kepler's third law'.

Caveat: catalogues often *derive* semi-major axes from the period and stellar mass via Kepler's law, so this check validates the pipeline on real catalogue data rather than testing Kepler's law independently.

## 2. Radius versus irradiation and mass

620 giant planets (0.3–13 Jupiter masses) with measured mass and radius. Every model below was fitted in log-radius and scored by 10-fold cross-validation (CV) and BIC (lower is better).

| Rank | Model | Params | CV error (dex) | BIC |
|---|---|---|---|---|
| 1 | Euresis: R = [a·x^p·exp(b·x^r)](F) · M^c | 5 | 0.0989 | -1822.3 |
| 2 | Euresis: R = [(a + b·x^p)^q](F) · M^c | 5 | 0.0997 | -1803.8 |
| 3 | Euresis: R = [a + b·x^p](F) · M^c | 4 | 0.1014 | -1788.4 |
| 4 | Euresis: R = [a·exp(b·x^p)](F) · M^c | 4 | 0.1019 | -1782.7 |
| 5 | quadratic in log M and log F | 5 | 0.1102 | -1734.3 |
| 6 | Euresis: R = [a/(exp(b·x^p) + c)](F) · M^c | 5 | 0.1000 | -1712.3 |
| 7 | power law  R = C·M^a·F^b  (Weiss et al. 2013 form) | 3 | 0.1117 | -1671.6 |
| 8 | Euresis: R = [a·x^p](F) · M^c | 3 | 0.1117 | -1671.6 |
| 9 | Euresis: R = [a·log(1 + b·x)](F) · M^c | 3 | 0.1121 | -1666.5 |
| 10 | Euresis: R = [a·x^p/(b + x^p)](F) · M^c | 4 | 0.1117 | -1665.2 |

**Best law (by BIC): Euresis: R = [a·x^p·exp(b·x^r)](F) · M^c**, parameters 0.9623, -0.0402, 0.06141, 0.3152, -0.04728.

It explains the data with a CV error of 0.0989 dex, versus 0.1117 dex for the published-style power law and 0.1142 dex for a constant radius.

## 3. Residuals

- residual vs FeH: Spearman ρ = -0.145 (n = 571)
- residual vs age: Spearman ρ = +0.009 (n = 174)
- residual vs Teq: Spearman ρ = +0.000 (n = 620)

## Honest assessment

* Published empirical relations exist for this anomaly. For example, Weiss et al. (2013) give R ∝ M^−0.04 F^0.094 for giant planets, and Thorngren & Fortney (2018) infer a heating efficiency that peaks near Teq ≈ 1500 K. These are cited from memory: the literature search could not run in this environment, so the novelty of any result here is **unchecked**.
* A better-fitting functional form on one catalogue is a *candidate* empirical law, not a discovery. To become one it must hold on independent, homogeneous data (for example, the NASA Exoplanet Archive with uniform stellar parameters), be compared against the literature, and ideally be explained physically.
