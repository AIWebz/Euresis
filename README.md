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
| Formulas | **185** core laws across 23 fields: mechanics, gravitation, waves, optics, thermodynamics, statistical mechanics, electromagnetism, circuits, fluids, materials, relativity, quantum, atomic, nuclear, astrophysics, chemistry, biology, earth science, information theory |
| Principles | **60** foundational statements: Newton's laws, conservation laws, the laws of thermodynamics, Maxwell's equations, the Schrödinger equation, Noether's theorem, evolution, the central dogma, plate tectonics, Big Bang cosmology, the scientific method… |
| Constants | **31** fundamental constants (CODATA 2018, with the exact SI-defined values marked as exact) |
| Quantities | **218** physical quantities, each with its SI dimension |
| Frontier | **18** open problems (quantum gravity, dark matter, the hierarchy problem, origin of life, P vs NP…) for exploration to aim at |

Every formula is parsed with SymPy and **checked for dimensional consistency when
it loads**. A formula with mismatched units is rejected.

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
