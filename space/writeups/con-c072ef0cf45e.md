# G (Catalan): continued fraction a(n) = 3n² + 11n + 9, b(n) = -2·n^2·(n + 2)^2 equals (4) / (-5 + 6·G (Catalan))

*Claim `con-c072ef0cf45e` · source: `euresis/novelty_math.py` · status: **numerically verified, not proved***

## Statement

G (Catalan): continued fraction a(n) = 3n² + 11n + 9, b(n) = -2·n^2·(n + 2)^2 equals (4) / (-5 + 6·G (Catalan))

Exact payload checked by the verifier:

```json
{
 "a": "3*n**2 + 11*n + 9",
 "b": "-2*n**2*(n + 2)**2",
 "digits": 100,
 "value": "(4) / (-5 + 6*catalan)"
}
```

## Method

Found by a Ramanujan-Machine-style search over polynomial continued fractions; the fraction is evaluated with mpmath at two depths (to show convergence) and compared with the closed form. This is numerical evidence, not a proof.

## Evidence

```json
{
 "depths": [
  2000,
  4000
 ],
 "digits_agree": 130.0,
 "digits_converged": 130.0,
 "note": "numerical agreement is evidence, not proof"
}
```

## Novelty

not in classical families or the Ramanujan Machine's published search domains; LIReC/OEIS/arXiv not checked.

Before this is called new, an expert should check the literature this environment could not reach.

## Reproduce

```bash
python -m euresis gate --recheck   # re-runs every verifier
```
