# Euresis — proven discoveries (sharp inequalities)

Each theorem was found numerically, then **proved** for all positive a, b, c by the Z3 theorem prover (complete decision procedure for real polynomial inequalities), and checked for sharpness: a constant 0.1% larger is refuted by Z3 with a counterexample.

Pairs examined: 16. Time: 0.1 min.

## Result

**For all positive real numbers a, b, c:**

  [a/(b+c)+b/(c+a)+c/(a+b)] − 3/2  ≥  **1** · ([3(a²+b²+c²)/(a+b+c)²] − 1)

and the constant 1 cannot be improved (tight near b/a = 1.0, c/a = 0.0).

Status: **proven** (machine proof) and **sharp**. Novelty: not among the classical inequalities Euresis knows; the wider inequality literature (olympiad collections, journals) cannot be searched from this environment, so it may already be known.

## All proven inequalities

| P | Q | k* | Sharp | Status |
|---|---|---|---|---|
| (a²+b²+c²)/(ab+bc+ca) | a/(b+c)+b/(c+a)+c/(a+b) | 1 | yes | both sides classical (rearrangement / sum of squares, Nesbitt (1903)) — very likely already known |
| a/(b+c)+b/(c+a)+c/(a+b) | (a²+b²+c²)/(ab+bc+ca) | 1/2 | yes | both sides classical (Nesbitt (1903), rearrangement / sum of squares) — very likely already known |
| a/(b+c)+b/(c+a)+c/(a+b) | 3(a²+b²+c²)/(a+b+c)² | 1 | yes | not in Euresis' knowledge |
