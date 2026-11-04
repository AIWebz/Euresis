# Euresis

**Euresis** (Greek *heúresis*, "discovery") is a scientific discovery engine. It
starts from a knowledge base of established science and builds on it: it derives
new relations, finds analogies between fields, works out natural scales, asks
questions where its knowledge has gaps, and checks its predictions against
measurements. Every thought it has is stored in an unbounded **Thought Space**,
which you can explore as an infinite canvas.

> **What Euresis is and is not.** It is not a large language model, and it was not
> trained on "all of science". That would take a data-centre-scale training run.
> Euresis is a working, inspectable system: a curated, machine-checked knowledge
> base, a symbolic reasoning engine, and a small neural model trained from scratch
> on that knowledge. Every result can be traced back to the laws it came from.
> `euresis ask` can also use Claude as its language interface, grounded in Euresis'
> knowledge (optional).

## What it knows

| | |
|---|---|
| Formulas | **391** laws across 24 fields: geometry, mechanics, gravitation, waves, optics, thermodynamics, statistical mechanics, electromagnetism, circuits, fluids, materials, relativity, quantum, atomic, nuclear, astrophysics & cosmology, chemistry, biology (genetics, ecology, physiology, neuroscience, epidemiology), earth & climate science, information theory |
| Principles | **128** foundational statements: Newton's laws, conservation laws, the laws of thermodynamics, Maxwell's equations, the Schrödinger equation, Noether's theorem, evolution, the central dogma, plate tectonics, Big Bang cosmology, the scientific method… |
| Constants | **47** fundamental and astronomical constants (CODATA 2018, with the exact SI-defined values marked as exact) |
| Quantities | **372** physical quantities, each with its SI dimension |
| Frontier | **30** open problems (quantum gravity, dark matter, the Hubble tension, turbulence, origin of life, P vs NP…) for exploration to aim at |

Every formula is parsed with SymPy and **checked for dimensional consistency when
it loads**. A formula with mismatched units is rejected.

## Directive

Euresis explores under a standing goal, which is stored as the first thought in its Thought Space:

> Discover relations that are not yet part of established knowledge. Build on the laws you were
> given and on your own verified results; prefer bridges between different fields; check every
> candidate for dimensional consistency and against measurements; never present an untested
> candidate as established fact.

In practice this means:

* Results that turn out to be known laws are recorded, but they are not built on further.
* Results that are not in the knowledge base are ranked by novelty. The score rewards bridging
  several fields, depth of the derivation chain, and the trained model's plausibility estimate.
  The top results feed the next cycle.
* After each run, the highest-ranked candidates are written to `space/discoveries.md`, each with
  its full derivation chain.

## Feeding it more knowledge

Put new knowledge in a text file, one item per line, then run `python -m euresis learn myfile.txt`.
Euresis validates every formula (malformed or dimensionally inconsistent lines are rejected and
listed), stores the file in `euresis/knowledge/user/`, and retrains its model.

```
formula   | chemistry | Arrhenius equation | k = A*exp(-Ea/(R*T)) | k:rate_constant A:pre_exponential Ea:activation_energy T:temperature
principle | biology   | Cell theory | All living things are made of cells.
quantity  | magnetic_susceptibility | magnetic susceptibility | 1
constant  | G_F | Fermi coupling constant | 4.5437957e-14 | J^-2 | M-2 L-4 T4
frontier  | physics   | Nature of dark energy | q:energy_density c:G
```

## How it builds on what we know

Each exploration cycle runs these strategies and writes every step into the
Thought Space, linked to the thoughts it came from:

1. **Structural analogy.** Find laws with the same mathematical form in different
   fields (Newton's gravity ≅ Coulomb's law, kinetic energy ≅ capacitor energy,
   radioactive decay ≅ first-order kinetics), then carry other laws across the
   analogy.
2. **Natural scales.** Dimensional analysis (Rayleigh's method and Buckingham Π)
   on sets of constants. This recovers the Planck units, the Bohr radius (up to
   4π), the Compton wavelength, the fine-structure constant α and the
   gravitational coupling α_G. It also gives the insight that gravity is about
   10³⁶ times weaker than electromagnetism.
3. **Gap questions.** The trained concept model predicts links between quantities
   that no known law connects. Euresis asks the question and tries a dimensional
   answer.
4. **Dimensional sweep.** Finds the most plausible scaling law for each quantity
   from inputs chosen by the model.
5. **Composition.** Eliminates a shared quantity between two laws to derive a new
   one. Relations from earlier cycles are combined first, so the results build on
   each other.
6. **Prediction.** Evaluates new relations on real systems (Earth, the Sun, a
   pendulum) and compares them with measured values. For dimensional-analysis
   results, the measurement calibrates the unknown prefactor.

Each result is classified against the knowledge base as one of: *re-derived known
law*, *same form as a known law but a different coefficient*, or *new to Euresis
(dimensionally consistent)*. A "new" result is a **hypothesis**. It is dimensionally
sound and logically derived, but it has not been tested by experiment.

## Discovering laws in data

`python -m euresis discover` looks for laws in real measurements. Euresis then checks each one
against unit analysis and against what it already knows:

* **Orbits** (8 planets, 4 Galilean moons, the Moon, GPS and geostationary orbits; NASA data).
  Fitting the data alone gives T ∝ a^1.4989 · M^−0.4992. Unit analysis requires 3/2 and −1/2, so
  the two agree. The prefactor is 6.2755 ≈ 2π, which recovers Kepler's third law.
* **Hydrogen Balmer lines** (6 wavelengths, NIST). The data give 1/λ = R(1/2² − 1/n²). The fitted R
  is 0.055% below the Rydberg constant, and Euresis explains the gap as 1/(1 + m_e/m_p). That is the
  reduced-mass correction: the electron orbits the centre of mass, not the nucleus itself.
* **Simulated pendulum and projectile** (Euresis' own simulators). The data give
  period = 2π·√(L/g) and range = v²/g at 45°. The exponents match unit analysis, the prefactors
  come out as 2π and 1, and each result is matched to the known law.
* **Atmosphere** (U.S. Standard Atmosphere 1976). An exponential fits with a scale height of 6.7 km.
  Combined with H = RT/(Mg), this implies a mean air temperature of 229 K. The fit is only accurate
  to about 5%, because the real atmosphere is not one temperature.

You can analyse your own data:

```bash
python -m euresis discover --csv mydata.csv --target y --map x:length y:period
```

## Idea engine (Claude proposes, Euresis verifies)

`python -m euresis connect` finds *connection points*: laws from distant fields that share a
quantity. For each one, it gives Claude the surrounding knowledge and asks for new ideas that
connect the pieces. Each idea must come back with an equation, the meaning of every symbol, the
laws it builds on, a prediction and a test. Euresis then checks every idea itself:

* Does the equation parse?
* Is it dimensionally consistent?
* Is it already a known law?
* Do the laws it cites exist?

Each idea is recorded as verified, already known, or rejected. Passing these checks means an idea
is well-formed, not that it is true. Each one still needs the experimental test it was proposed with.

This needs the `anthropic` package and credentials (`ANTHROPIC_API_KEY`, or `ant auth login`).
Without them, the connection points are still recorded as open questions.

## Scorecard: law discovery from data

`python -m euresis lawbench` takes every law in the knowledge base that has a single unknown on one
side (345 laws in 24 fields), hides the formula, and hands Euresis only data and the SI units of each
column. It follows the AI Feynman protocol (Udrescu & Tegmark, 2020):

* every input, physical constants included, is sampled uniformly from [1, 5], 400 rows per law;
* a result counts as **exact** only if the recovered *symbolic* equation reproduces the true law on
  fresh, unseen data to within 10⁻⁶.

| Version | Exact | Approximate | Missed |
|---|---|---|---|
| First engine (unit analysis + 14 formula shapes), noiseless data | 271 / 345 (78.6%) | 30 | 44 |
| Current engine, noiseless data | **337 / 345 (97.7%)** | 2 | 6 |
| Current engine, **1% Gaussian noise** on the target | **289 / 345 (83.8%)** | 36 | 20 |

"Exact" under noise means that the equation recovered from noisy data matches the *noiseless* true
law to 10⁻⁶ on fresh data. In other words, it is the law itself, not a curve fitted to the noise.
With noisy data, Euresis identifies constants only as precisely as the noise allows, collects every
closed-form candidate, and keeps the simplest one that fits as well as the noise permits.

The current engine added:

* formula shapes that can be solved directly instead of by trial and error (ratios of terms; sums of
  terms and logarithms);
* shapes where an exponent is itself a variable;
* closed-form recognition of constants (rational × π^a · 2^b · 3^c · 5^d · ln 2 / ln 10), with a
  guard against contrived matches;
* stopping as soon as an exact answer is found;
* noise-aware model selection.

Laws recovered exactly include Planck's black-body law, the Lorentz factor, relativistic velocity
addition and Doppler shift, the Arrhenius and Eyring equations, Michaelis–Menten and Hill kinetics,
the Otto-cycle efficiency, Shannon–Hartley capacity, the Fermi energy (3^(2/3)·π^(4/3)·ħ²n^(2/3)/2mₑ),
the Hawking temperature, and the Jeans mass.

Still missed:

* the Nernst equation;
* capillary rise;
* the semi-empirical nuclear mass formula (4 terms);
* beam attenuation;
* competitive enzyme inhibition;
* earthquake moment magnitude.

Two laws are only approximate, correctly, because they contain empirical numbers with no closed form:
the Chandrasekhar limit (0.7744…) and main-sequence lifetime.

**Context.** AI Feynman reported 100 of 100 equations on its own benchmark, the Feynman Symbolic
Regression Database. This benchmark is a different and larger set (345 laws across physics,
chemistry, biology, earth science and information theory), so the numbers are not directly
comparable. Running Euresis on the public Feynman/SRSD datasets is the next step for a
like-for-like comparison. Those datasets aren't downloadable from this environment.

Per-law results: `space/srbench_clean.json` (no noise) and `space/srbench_noise10.json` (1% noise).

## The reasoning core (Claude + verified tools)

`python -m euresis research "your question"` runs Claude (`claude-opus-5-5`, adaptive thinking) as
the reasoning core. Claude does the open-ended work: reading, connecting fields, and designing
derivations and experiments. **Claude proposes; only verifiers decide.** It records its hypotheses
and plan with `propose`, and every claim it wants to report must go through `submit_claim`, which
writes it to the claims registry (`registry.py`) and runs the verification gate (`gate.py`) for its
kind. The status comes from the verifier, never from the model, and there is no ungated prover tool.
A claim counts as a discovery only when it is proved and not known. Claude may flag a result as
known (`known_as`). Otherwise a proved claim is checked against the literature, and a close match
marks it known.

The final report is built in two parts. Every claim id that Claude cites, such as `[z3-0123456789ab]`,
is rewritten with the status the gate recorded, and an id that isn't in the registry is marked
*NOT IN REGISTRY — unverified*. Euresis then appends the authoritative claim table, the totals, the
discoveries, any submitted claims the narrative left out, and the hypotheses (labelled as not
results). The report is saved to `space/research/` and the claims to `space/claims.json`. If a run
stops early, the claims gated so far are still reported.

```bash
python -m euresis claude-ping       # one test call: confirms credentials, never prints the key
```

```bash
python -m euresis research "largest k with a/(b+c)+b/(c+a)+c/(a+b)-3/2 >= k((a²+b²+c²)/(ab+bc+ca)-1)?"
```

| Layer | Tool | What it does |
|---|---|---|
| Knowledge | `search_knowledge` | 391 laws, 128 principles, 47 constants, plus Euresis' own past results |
| Literature | `search_literature`, `check_novelty` | arXiv, PubMed, Semantic Scholar and OpenAlex, plus a local SQLite full-text index that grows with every search |
| Exact maths | `computer_algebra`, `check_dimensions` | SymPy, and Euresis' dimensional analysis |
| Planning | `propose` | Hypotheses and research plan, stored in the Thought Space as hypotheses, never as results |
| Gate | `submit_claim` | Claim → registry → verifier for its kind: Z3 (`z3`, `inequality`, `physics-relation`), SymPy + mpmath (`identity`, `constant`), Lean 4 (`lean`), interval arithmetic (`orbit`, queued) |
| Simulation | `simulate`, `run_experiment` | Nonlinear ODE models for physics (pendulum, orbits, projectiles, oscillators, RLC circuits, heat diffusion), chemistry (mass-action kinetics, Arrhenius) and climate (energy balance with ice-albedo feedback). Parameter sweeps feed the law search. |
| Code | `run_python` | Sandboxed Python (numpy, scipy, sympy), with no network access, CPU/memory limits and a timeout |
| Memory | `record_idea` | Re-verifies each idea, checks it against the literature, and stores it in the Thought Space |

Every tool call and every idea is written to the Thought Space. `connect` now also runs the
literature novelty check on each verified idea.

Each layer can also be used directly:

```bash
python -m euresis literature search black hole entropy
```

```bash
python -m euresis literature harvest "dark matter rotation curves" -n 200
```

```bash
python -m euresis literature novelty "pendulum period grows with amplitude as theta^2/16"
```

```bash
python -m euresis simulate pendulum length=1 theta0=1.5
```

```bash
python -m euresis simulate ebm co2_ppm=560
```

```bash
python -m euresis prove "x**2 + y**2 >= 2*x*y" --vars x:Real y:Real
```

```bash
python -m euresis sandbox script.py
```

**Requirements.**

* **Claude credentials** for `research` and `connect`: `ANTHROPIC_API_KEY`, or `ant auth login`.
* **Network access to the literature APIs**: `export.arxiv.org`, `eutils.ncbi.nlm.nih.gov`,
  `api.semanticscholar.org` and `api.openalex.org`. If they can't be reached, novelty is reported
  as *unchecked*, never guessed.
* **Lean 4** (optional), installed with elan.

## Mathematical discovery: formulas for fundamental constants

`python -m euresis conjecture [basic|frontier|sweep]` searches polynomial continued fractions,
using the Ramanujan Machine method (Raayoni et al., *Nature* 2021). Each run has four stages:

1. Screen every continued fraction in double precision.
2. Match each limit against Möbius transforms (p + q·c)/(r + s·c) of 18 constants.
3. Re-verify each match with 120-digit arithmetic at two depths.
4. Discard classical and reducible families.

| Search | Fractions screened | Verified ≥ 60 digits | Irreducible, outside classical families |
|---|---|---|---|
| basic (linear / quadratic / cubic a(n)) | 203,167 | 78 | 3 |
| frontier (Apéry-type cubics, ζ(5)-oriented quintics) | 329,778 | 2 | 1 |
| sweep (quadratic a(n), quartic b(n)) | 319,616 | 78 | 13 |

Notable results include 8/(7ζ(3)) = 1 − 1⁶/(21 − 2⁶/(95 − 3⁶/(259 − …))) and
1/(2G) = 1 − 2·1⁴/(7 − 2·2⁴/(19 − 2·3⁴/(37 − …))), where G is Catalan's constant. They appear to
match formulas first reported by the Ramanujan Machine in 2021, so they were rediscovered
independently, not discovered.

No formula for ζ(5) was found in the searched families.

**The novelty of every candidate is unverified.** The published catalogues (Ramanujan Machine
database, OEIS, arXiv) are not reachable from this environment. Results:
`space/conjectures.md`, `space/conjectures_frontier.md`, `space/conjectures_sweep.md`.

## Proven discoveries: sharp inequalities

`python -m euresis prove-new` searches pairs of symmetric expressions in positive a, b, c. For each
pair it finds the best constant numerically, then **proves** the inequality with the Z3 theorem prover,
a complete decision procedure for real polynomial inequalities. It confirms the constant is sharp
(Z3 refutes a constant 0.1% larger) and runs until it has a proven, sharp theorem that goes beyond the
classical inequalities it knows.

First result, found and proved in 3.5 s:

> For all positive real a, b, c: a/(b+c) + b/(c+a) + c/(a+b) − 3/2 ≥ 3(a²+b²+c²)/(a+b+c)² − 1,
> with equality approached at a = b, c → 0. The constant 1 is best possible.

Independent checks found no counterexample in 1,000,000 random points or in 2,000 exact rational
points. The difference of the two sides factors as a degree-5 symmetric polynomial over a positive
denominator.

It is **proven**. Its **novelty is unverified**: the inequality literature cannot be searched from this
environment, and a statement this compact may well already be known.

## Live model: the three-body problem

`euresis/threebody.py` turns Euresis' law of gravity into a live simulation of three equal masses. It
then explores that simulation for **periodic orbits**: motions that repeat exactly, which are rare and
which physicists still search for.

The search ran in four steps:

1. **Screen:** simulate 57,836 starting velocities to time 40.
2. **Shortlist:** 1,066 motions came back close to their start.
3. **Refine:** confirm 5 distinct periodic orbits that close to better than 10⁻⁸.
4. **Check:** compare each orbit with Li & Liao's catalogue of 695 equal-mass orbits
   (github.com/sjtu-liao/three-body), using starting velocities and the scale-invariant period
   T* = T·|E|^{3/2}.

Results:

| Orbit (v₁, v₂) | T* | Status |
|---|---|---|
| (0.3471, 0.5327) | 9.238 | figure-eight, catalogue I.A1: rediscovered |
| (0.3394, 0.5362) | 9.238 | the same figure-eight, seen from another starting point |
| (0.4644, 0.3961) | 24.206 | catalogue I.B1: rediscovered |
| (0.1819, 0.5148) | 36.909 | **not in the catalogue**; closes to 10⁻⁸ over 3 periods; collision-free |
| (0.1890, 0.5398) | 36.940 | **not in the catalogue**; periodic to 8 × 10⁻⁹; unstable |

The two orbits that are not in the catalogue have T* close to 4 × the figure-eight's, so they
look like "satellites" of the figure-eight. Šuvakov (2014) searched exactly that family of orbits, and
that paper could not be checked here. They are therefore **candidates**, not confirmed discoveries.

The interactive Orbit Lab (`space/orbit_lab.html`) plays every orbit and includes a live-physics mode.

## Answering questions from measured knowledge

`python -m euresis answer "<question>"` answers questions from measured facts (`euresis/knowledge/facts.py`).
Each fact comes with its source: the composition of the universe (Planck 2018), dry air, the Sun,
the human body, Earth's crust, seawater and atoms. For each answer, Euresis:

* finds the facts relevant to the question;
* works out which components add up to any percentage the question names;
* evaluates its own laws on the measured numbers;
* explains how we know (its principles) and what is still unknown (its open problems).

The mystery solver uses this first.

For example, *"What is 95% of our universe actually made of?"* gives:

* **dark energy (68.9%) + dark matter (26.1%) = 95%**, with ordinary matter the remaining ~5%;
* from its critical-density law and the measured expansion rate, a critical density of
  8.6 × 10⁻²⁷ kg/m³, about 5 proton masses per cubic metre, of which ordinary matter is only 0.25;
* how we know (galaxy rotation curves, accelerating expansion, the cosmic microwave background);
* that *what* dark energy and dark matter are is still undiscovered.

Questions it has no facts for are answered honestly: "Euresis has no measured facts that answer
this question."

## Reading the literature and discovering while reading

Euresis has read **195,654 real abstracts** of published clinical trials (PubMed 200k RCT,
Dernoncourt & Lee 2017). All of them are indexed in its local full-text library, so offline literature
search works for medicine. `python -m euresis read-papers` rebuilds the library and reruns discovery.

While reading the papers in publication order, Euresis generates **literature-based discovery**
hypotheses (Swanson's ABC model): concepts never mentioned together, but strongly linked through
shared intermediate concepts.

**Measured (time-sliced).** Hypotheses were built from the first 156,523 papers only, then checked
against the next 39,131:

| | Predicted links later published |
|---|---|
| **Euresis** | **127 / 500 (25.4%)** |
| Frequency-matched random pairs | 2.2% |

That is 11.5× better than chance: Euresis predicts connections before they appear in the literature.

**Limits.** Its open hypotheses from all 195k papers are mostly links between neighbouring topics
within one field (dentistry materials, eye surgery). Separating medically surprising links would
need concept types (drug, disease, gene), which this text-only method lacks. The corpus is clinical
trials only, not "millions of papers": the large paper databases are not reachable from this
environment.

**Euresis-LM 2** (`models/euresis-lm2-ft`) is a 6.9 M-parameter transformer with an 8,192-token
vocabulary. It was trained on 25 M tokens (60 k abstracts plus Euresis' knowledge), then fine-tuned.
It absorbed medical language: 1.28 bits/char on unseen abstracts, against 6.49 for Euresis-LM 1.
But it lost Euresis-LM 1's science-question understanding. Euresis therefore uses two specialists:
`--model science` (LM 1, the default, used by the mystery solver) and `--model papers` (LM 2).

## Euresis-LM: its own language model

Euresis-LM is a GPT-style transformer, written from scratch in JAX (`euresis/lm/`) and trained on
CPU from Euresis' own knowledge:

* **Architecture:** 6 decoder layers, d = 256, 8 attention heads, a 128-token context, and a
  byte-level BPE tokenizer with a 4,096-token vocabulary.
* **Size:** 5.8 M parameters.
* **Training:** 554 k tokens of laws, principles, constants, quantities, explanations and
  question → law pairs; 1,500 AdamW steps; about 29 minutes.
* **Overfitting control:** early stopping on held-out loss. A first run overfit and was discarded.
  Best held-out loss: 0.569.

It is used for language understanding: deciding which laws a question is about, inside the mystery
solver. It also writes short explanations (`python -m euresis lm explain "Ohm's law"`).

**Measured (`python -m euresis lm eval`)** on questions it never saw in training:

| Method | Held-out phrasings: top-1 / top-5 | Everyday questions: top-1 / top-5 |
|---|---|---|
| Word matching (previous) | 68.0% / 92.0% | 16.7% / 25.0% |
| Euresis-LM alone | 64.0% / 84.7% | 8.3% / 12.5% |
| **Word matching + Euresis-LM (used)** | **74.0% / 95.3%** | 12.5% / 25.0% |

**Limits.** Euresis-LM learned only from Euresis' knowledge base. It understands scientific phrasing
but lacks world knowledge: it does not know that "leaving Earth" means escape velocity. It is
millions of times smaller than frontier language models and does not reason like them. More text
would be the biggest improvement, either a large public-domain science corpus or a pretrained
open-weight model. Neither is downloadable from this environment.

Commands:

```bash
python -m euresis lm train
```

```bash
python -m euresis lm eval
```

```bash
python -m euresis lm ask "How hot is a black hole?"
```

```bash
python -m euresis lm explain "Ohm's law"
```

```bash
python -m euresis lm generate "question: why do stars shine?"
```

## The trained model

`euresis/model.py` trains two components from scratch in pure NumPy:

* **Concept embedding.** A link-prediction model (logistic matrix factorisation
  with negative sampling) over the 249 quantities, constants and fields that
  appear together in laws of nature. On held-out relations it scores a
  **link-prediction AUC of ≈ 0.96** (see `models/metrics.json`). The explorer uses
  it to judge which relations are plausible, which inputs to try in dimensional
  analysis, and how to re-type quantities carried across an analogy.
* **Text retriever.** TF-IDF plus latent semantic analysis over the whole corpus,
  used by `euresis ask`.

## Rediscovery benchmark

To show that Euresis can really find laws, `euresis benchmark` removes 10 famous
laws from the knowledge base **and** from the model's training data, explores
from what is left, and checks whether any output matches a removed law (exactly,
or up to a dimensionless factor that dimensional analysis cannot fix). The latest
result is saved in `space/benchmark.json` and shown on the canvas.

## Local 14B language model (no API needed)

Euresis can use **Qwen3-14B** (14.8 B parameters, Apache-2.0, by the Qwen team) as its reasoning core. The model
runs on the CPU through llama.cpp at 4-bit quantisation, which needs 9 GB of disk and about 12 GB of RAM. It
drives the same verified tools Claude does: knowledge search, computer algebra, dimensional checks, Z3,
simulators, sandboxed Python, and `submit_claim`, which sends a formal claim through the verification gate. The
gate's verdict, not the model, decides whether a claim is proved. On 4 CPU cores it writes a few tokens per
second, so a research run takes minutes rather than seconds.

```bash
pip install llama-cpp-python
python -m euresis local download                       # 9.0 GB → data/models/
python -m euresis local chat "Why is the sky blue?"
python -m euresis research "..." --backend local       # reasoning core with tools
python -m euresis ask "..."                            # written answer (Claude if a key is set, else local)
```

`--backend auto` (the default) uses Claude when `ANTHROPIC_API_KEY` is set and the local model otherwise.

## Verification gate, claims registry, scorecard

Nothing Euresis says counts until a machine has checked it.

* **Claims registry** (`euresis/registry.py`). Every candidate result is stored as a claim with an exact,
  machine-checkable payload. Claims live in a SQLite database (`data/registry.db`) and are exported to
  `space/claims.json`, which is committed and rebuilds the database on a new machine.
* **Verification gate** (`euresis/gate.py`). Each kind of claim goes to a verifier that can decide it:
  Z3 for inequalities and algebra (cross-checked by random sampling), SymPy plus 50-digit arithmetic for
  identities, mpmath for continued fractions, kv interval arithmetic with a Krawczyk test for three-body
  orbits, and Lean 4 when installed. Statuses: `proved`, `verified-numeric` (evidence, not proof), `refuted`
  (a counterexample was found) and `unverified` (a failed proof attempt, which is not a refutation). Only the
  gate can change a status. A **discovery** must be *proved* and not known.
* **Job queue** (`euresis/jobs.py`). Long proofs, such as orbits that take hours, run as queued jobs stored in
  the database. A job left running by a crashed worker is put back in the queue.
* **Scorecard** (`space/scorecard.md`). This page includes the gate self-test: 12 claims with known answers,
  where every true one must be proved and every false one refuted. It also shows the latest benchmarks and
  every claim with its honest status.
* **Write-ups for expert review** (`space/writeups/`). Each claim that passed the gate and is not known gets
  a one-page note (Markdown and LaTeX) with its statement, method, evidence, what was and was not searched
  for novelty, and the commands that reproduce it.
* **Rigorous three-body proofs** (`euresis/proofs/`). These are computer-assisted existence proofs of periodic
  orbits; see `euresis/proofs/README.md`.

```bash
python -m euresis collect      # bring engine results into the registry
python -m euresis gate         # verify everything; slow proofs are queued
python -m euresis jobs work    # process queued proofs
python -m euresis claims       # list claims with their status
python -m euresis scorecard    # self-test + benchmarks + claims → space/scorecard.md
python -m euresis writeup      # notes for expert review → space/writeups/
```

The package installs with `pip install -e .` (this provides the `euresis` command). CI (`.github/workflows/ci.yml`)
runs the tests and the gate self-test on every push and compiles the orbit prover.

## Usage

```bash
pip install -r requirements.txt
```

```bash
python -m euresis info                      # what Euresis knows
```

```bash
python -m euresis train                     # train the concept model
```

```bash
python -m euresis explore --fresh --cycles 3   # explore and write space/space.html
```

```bash
python -m euresis explore --cycles 2        # keep building on the existing space
```

```bash
python -m euresis benchmark                 # rediscovery test
```

```bash
python -m euresis solve "escape velocity" escape_velocity mass=5.97217e24 radius=6.378137e6
```

```bash
python -m euresis ask "how fast must a rocket go to leave a planet?"
```

```bash
node scripts/screenshot.mjs                 # screenshots in space/screenshots/
```

```bash
python -m pytest -q tests
```

Open `space/space.html` in a browser to explore the Thought Space: drag to pan,
scroll to zoom, click a thought to see what it was built from and what it led to,
click a legend chip to toggle a kind, or search.

## Layout

```
euresis/
  knowledge/   quantities, constants, formulas & principles, frontier problems
  dimensions.py  SI dimension algebra
  kb.py        loading, parsing, dimensional checking
  engine.py    solve, evaluate, dimensional analysis, composition, analogy, equivalence
  model.py     trained concept embedding + text retriever
  explorer.py  the discovery loop
  space.py     the append-only Thought Space (space/thoughts.jsonl)
  render.py    layout + infinite-canvas export (templates/space.html)
  benchmark.py rediscovery benchmark
  llm.py       optional Claude language backend
```
