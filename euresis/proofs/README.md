# Computer-assisted proofs

`threebody_proof.cc` gives a rigorous existence proof (interval arithmetic plus a
validated ODE solver, using the kv library) for symmetric periodic orbits of the
planar equal-mass three-body problem (G = m = 1).

**Setup.** Unknowns are x = (p1, p2, τ). The initial state is
r1 = (−1,0), r2 = (1,0), r3 = 0, v1 = v2 = (p1,p2), v3 = −2(p1,p2). This state lies
in Fix(R) for the time-reversing symmetry R(r_i, v_i) = (−r_σ(i), v_σ(i)), where σ swaps 1 and 2.

**Equations.** F(x) = ( x3(τ), y3(τ), (v1−v2)(τ)·r1(τ) ) = 0. Linear momentum P = 0
and angular momentum L = 0 are conserved, so F = 0 gives z(τ) ∈ Fix(R). The orbit
is then periodic with period 2τ.

**Proof.** kv's `odelong_maffine` integrates the equations of motion together with
their variational equations, giving rigorous enclosures. The Krawczyk operator
K(I) = c − R F(c) + (Id − R F′(I))(I − c) is evaluated with interval arithmetic.
If K(I) ⊂ int(I), F has exactly one zero in I. A successful validated integration
also shows that no collision happens on [0, τ].

Build:

    g++ -O3 -DNDEBUG -I data/external/verified/kv euresis/proofs/threebody_proof.cc -o tbproof
    KV_RADII="1e-9 1e-8" ./tbproof p1 p2 tau 30

Results are in `results.md`.
