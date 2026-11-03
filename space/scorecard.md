# Euresis scorecard

Generated 2026-11-03 by `python -m euresis scorecard`.

## 1. Verification gate self-test

**12/12** known-true claims proved and known-false claims refuted.

| Claim | Expected | Got | |
|---|---|---|---|
| AM–GM: (a+b+c)³ ≥ 27abc (true) | proved | proved | ✓ |
| (a+b+c)³/27abc − 1 ≥ (a²+b²+c²)/(ab+bc+ca) − 1 (false at a=b=1, c=2) | refuted | refuted | ✓ |
| Nesbitt bound with constant 2 (false: sharp constant is 1) | refuted | refuted | ✓ |
| x² + y² ≥ 2xy | proved | proved | ✓ |
| x² ≥ x for all real x (false at x = 1/2) | refuted | refuted | ✓ |
| sin² + cos² = 1 | proved | proved | ✓ |
| (x+y)² = x² + y² (false) | refuted | refuted | ✓ |
| 4/π = 1 + 1/(3 + 4/(5 + 9/(7 + …))) (true) | verified-numeric | verified-numeric | ✓ |
| the same fraction equals 4/π + 10⁻⁴⁰ (false at digit 40) | refuted | refuted | ✓ |
| 2 + 1/(2 + 1/(2 + …)) = 1 + √2 (true) | verified-numeric | verified-numeric | ✓ |
| relativistic K ≤ E (true) | proved | proved | ✓ |
| classical KE ≥ relativistic KE (false) | refuted | refuted | ✓ |

## 2. Benchmarks

| Benchmark | Result | Run | Source |
|---|---|---|---|
| Rediscovery of held-out laws | 4/10 recovered (2 exactly) | 2026-11-02 | `space/benchmark.json` |
| Symbolic regression, 345 laws (no noise) | 337/345 exact (97.7%) | 2026-11-02 | `space/srbench_clean.json` |
| Symbolic regression, 345 laws (1% noise) | 289/345 exact (83.8%) | 2026-11-02 | `space/srbench_noise10.json` |
| Literature-based discovery, time-sliced (PubMed) | 127/500 predicted links later published (25.4%) vs 2.2% for random pairs | 2026-11-03 | `space/literature_discovery.md` |

## 3. Claims registry

Status counts: candidate: 3, proved: 5, verified-numeric: 10

| Claim | Status | Verifier | Novelty |
|---|---|---|---|
| For all a,b,c > 0:  [(a²+b²+c²)/(ab+bc+ca)] − min  ≥  1 · ([a/(b+c)+b/(c+a)+c/(a+b)] − min) | **proved; already known** | z3+sampling | known (very likely: both sides classical) |
| For all a,b,c > 0:  [a/(b+c)+b/(c+a)+c/(a+b)] − min  ≥  1/2 · ([(a²+b²+c²)/(ab+bc+ca)] − min) | **proved; already known** | z3+sampling | known (very likely: both sides classical) |
| For all a,b,c > 0:  [a/(b+c)+b/(c+a)+c/(a+b)] − min  ≥  1 · ([3(a²+b²+c²)/(a+b+c)²] − min) | **proved; novelty: not among the classical inequalities Euresis knows; inequality literature not searched** | z3+sampling | not among the classical inequalities Euresis knows; inequality literature not searched |
| Relativistic kinetic energy ≤ total relativistic energy (all m, c > 0, 0 < v < c) | **proved; already known** | z3-sqrt | known (E = K + mc², so K ≤ E) |
| Periodic equal-mass three-body orbit with v = (0.3394074123, 0.5361849780), T ≈ 6.290819, T* ≈ 9.238 | **proved; already known** | kv-krawczyk | known (Li & Liao 2017 catalogue: I.A1 (same orbit, different starting point)) |
| G (Catalan): continued fraction a(n) = 3n² + 3n + 1, b(n) = -2·n^3·(n + 1) equals (-2) / (1 − 2·G (Catalan)) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| G (Catalan): continued fraction a(n) = 3n² + 3n + 1, b(n) = -2·n^4 equals (-1) / (-2·G (Catalan)) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| ln 2: continued fraction a(n) = 3n² + 6n + 2, b(n) = -2·n^3·(n + 2) equals (-2) / (-1 − ln 2) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| G (Catalan): continued fraction a(n) = 3n² + 7n + 3, b(n) = -2·n^3·(n + 2) equals (-2) / (1 − 2·G (Catalan)) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| G (Catalan): continued fraction a(n) = 3n² + 9n + 7, b(n) = -2·n·(n + 1)^3 equals (1) / (2 − 2·G (Catalan)) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| ln 2: continued fraction a(n) = 3n² + 10n + 6, b(n) = -2·n^2·(n + 2)^2 equals (-4) / (-5 + 6·ln 2) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| G (Catalan): continued fraction a(n) = 3n² + 11n + 9, b(n) = -2·n^2·(n + 2)^2 equals (4) / (-5 + 6·G (Catalan)) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| √3: continued fraction a(n) = 4n² + 12n + 7, b(n) = -1·n^2·(n + 2)^2 equals (-8 − 4·√3) / (-4 + √3) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| √3: continued fraction a(n) = 4n² + 12n + 9, b(n) = -1·n^2·(n + 2)^2 equals (-8 − 4·√3) / (-√3) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| ln 2: continued fraction a(n) = 10n² + 24n + 11, b(n) = -9·n^3·(n + 2) equals (4) / (-1 + 2·ln 2) | **numerically verified, not proved** | mpmath | not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked |
| Periodic equal-mass three-body orbit with v = (0.4644451728, 0.3960600147), T ≈ 14.894305, T* ≈ 24.206 | **not yet checked** | — | known (Li & Liao 2017 catalogue: I.B1) |
| Periodic equal-mass three-body orbit with v = (0.1819428805, 0.5148059977), T ≈ 18.141368, T* ≈ 36.909 | **not yet checked** | — | not in Li & Liao 2017 catalogue (695 families); newer catalogues (e.g. Hristov et al. 2022–2025) not checked — arXiv unreachable here |
| Periodic equal-mass three-body orbit with v = (0.1890048924, 0.5397624528), T ≈ 19.735392, T* ≈ 36.940 | **not yet checked** | — | not in Li & Liao 2017 catalogue (695 families); newer catalogues (e.g. Hristov et al. 2022–2025) not checked — arXiv unreachable here |

A claim counts as a **discovery** only when it is *proved* and not known. Discoveries by that rule: **1** — each still needs an expert literature check before it can be called new.
