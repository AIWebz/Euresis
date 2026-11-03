# For all a,b,c > 0:  [a/(b+c)+b/(c+a)+c/(a+b)] − min  ≥  1 · ([3(a²+b²+c²)/(a+b+c)²] − min)

*Claim `ine-1d5e9eb56bf3` · source: `euresis/theorems.py` · status: **proved; novelty: not among the classical inequalities Euresis knows; inequality literature not searched***

## Statement

For all a,b,c > 0:  [a/(b+c)+b/(c+a)+c/(a+b)] − min  ≥  1 · ([3(a²+b²+c²)/(a+b+c)²] − min)

Exact payload checked by the verifier:

```json
{
 "P": "a/(b + c) + b/(a + c) + c/(a + b)",
 "Q": "(3*a**2 + 3*b**2 + 3*c**2)/(a + b + c)**2",
 "k": "1"
}
```

## Method

Found by numerical minimisation of the ratio (P − min P)/(Q − min Q) and snapped to an exact rational. Proved with the Z3 SMT solver, which decides real polynomial inequalities completely: both sides are homogeneous of degree 0, so a = 1 without loss of generality, denominators are cleared and shown positive, and the negation of the numerator inequality is shown unsatisfiable. Cross-checked independently at 200 000 random points.

## Evidence

```json
{
 "samples": 200000,
 "sampling_min": 4.540349007875477e-08,
 "sharp": true,
 "z3": "proved"
}
```

## Novelty

not among the classical inequalities Euresis knows; inequality literature not searched.

Before this is called new, an expert should check the literature this environment could not reach.

## Reproduce

```bash
python -m euresis gate --recheck   # re-runs every verifier
```
