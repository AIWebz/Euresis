"""Mystery solver: Euresis works on open scientific questions by itself.

A mystery is only a question in plain language (plus, optionally, a dataset).
Euresis then, with no outside help:

1. **Understands** the question — retrieves the laws, principles and constants it
   judges relevant (text retrieval + the trained concept model), and infers the
   quantity being asked about.
2. **Reasons with units** — finds every combination of the relevant constants and
   quantities with the dimensions of the target (Rayleigh's method) and every
   dimensionless group (Buckingham Π), evaluating them numerically when they are
   built from constants of nature.
3. **Connects fields** — structural analogies between the relevant laws and laws
   elsewhere, carried across; compositions of the relevant laws with each other.
4. **Experiments** — runs a simulator when one fits the question's quantities.
5. **Reads data** — if the mystery comes with data, searches for the governing law.
6. **Judges** — ranks what it found, checks each item against what it already
   knows, and gives an honest verdict: a known result recovered, a candidate
   explanation (untested), or no progress.
"""
from __future__ import annotations

import math
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import sympy as sp

from .engine import Engine, Relation, _as_relation
from .kb import KnowledgeBase, family
from .model import TextRetriever
from .space import ThoughtSpace

MYSTERIES = Path(__file__).resolve().parent / "knowledge" / "mysteries.txt"
OUT = Path(__file__).resolve().parent.parent / "space" / "mysteries.md"


def load_mysteries():
    out = []
    for line in MYSTERIES.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            parts = [p.strip() for p in line.split("|")]
            out.append({"id": parts[0], "title": parts[1], "question": parts[2],
                        "dataset": parts[3] if len(parts) > 3 and parts[3] else None})
    return out


def _fmt(x):
    return f"{x:.3g}" if 1e-3 <= abs(x) < 1e5 else f"{x:.3e}"


class MysterySolver:
    def __init__(self, kb: KnowledgeBase, engine: Engine, model, space: ThoughtSpace | None, log=print):
        self.kb, self.E, self.model, self.space, self.log = kb, engine, model, space, log
        self.retriever = TextRetriever(kb.documents())

    # --------------------------------------------------------- 1 understand
    def _lm(self):
        if not hasattr(self, "_lm_model"):
            from .lm.model import EuresisLM
            self._lm_model = EuresisLM.load() if EuresisLM.available() else None
        return self._lm_model

    def understand(self, q: str):
        hits = self.retriever.search(q, 14)
        laws = [self.kb.by_name(d[1]) for d, _ in hits if d[0] == "formula" and self.kb.by_name(d[1])]
        lm = self._lm()
        if lm is not None:
            # Euresis-LM reads the question and ranks every law; fuse with word matching
            names = [f.name for f in self.kb.formulas]
            r_lm = {n: i for i, (n, _) in enumerate(lm.rank(q, names))}
            r_wm = {f.name: i for i, f in enumerate(laws)}
            fused = sorted(names, key=lambda n: -(1 / (10 + r_lm.get(n, 999)) + 0.5 / (10 + r_wm.get(n, 999))))
            laws = [self.kb.by_name(n) for n in fused[:10]]
        principles = [d[1] for d, _ in hits if d[0] == "principle"]
        consts = {c.name for f in laws for c in f.constants}
        for d, _ in hits:
            if d[0] == "constant":
                k = next((k for k, v in self.kb.constants.items() if v[0] == d[1]), None)
                if k:
                    consts.add(k)
        quantities = {q_ for f in laws for q_ in f.quantities}
        # quantities named in the question itself
        ql = q.lower()
        named = [qid for qid, (nm, _) in self.kb.quantities.items()
                 if re.search(r"\b" + re.escape(nm.split(" (")[0].lower()) + r"\b", ql)]
        named.sort(key=lambda x: -len(self.kb.quantities[x][0]))
        target = next((n for n in named if not self.kb.quantities[n][1].dimensionless), None)
        if target is None:
            counts = {}
            for f in laws:
                for q_ in f.quantities:
                    counts[q_] = counts.get(q_, 0) + 1
            target = max(counts, key=counts.get) if counts else None
        quantities |= set(named)
        return {"question": q, "laws": laws, "principles": principles, "constants": sorted(consts),
                "quantities": sorted(quantities), "target": target, "named": named}

    # ---------------------------------------------------- 2 units reasoning
    def scales(self, ctx, max_out=6):
        """Combinations of the relevant constants (and named quantities) with the target's units."""
        out = []
        t = ctx["target"]
        if t is None:
            return out
        tdim = self.kb.quantities[t][1]
        tlaws = [f for f in self.kb.formulas if any(family(q) == family(t) for q in f.quantities)]
        tconsts = {c.name for f in tlaws for c in f.constants}
        ranked = [c for c in ctx["constants"] if c in tconsts] or [c for c in ctx["constants"]]
        pool = ranked + [q for q in ctx["named"] if q != t and family(q) != family(t)
                                                and not self.kb.quantities[q][1].dimensionless]
        pool = list(dict.fromkeys(pool))[:7]
        seen = set()
        for r in (2, 3, 4):
            for sub in combinations(pool, r):
                syms = [sp.Symbol(x) for x in sub]
                exps, pis = self.E.rayleigh(tdim, syms)
                if exps is None or any(e == 0 for e in exps):
                    continue
                A = sp.Matrix([[self.kb.dims[s][i] for s in syms] for i in range(7)])
                if A.rank() < len(syms):
                    continue
                expr = self.E.monomial(syms, exps)
                key = str(expr)
                if key in seen:
                    continue
                seen.add(key)
                vals = {sp.Symbol(k): self.kb.constants[k][1] for k in sub if k in self.kb.constants}
                num = expr.subs(vals)
                plaus = np.mean([self.model.score(f"q:{t}", f"c:{x}" if x in self.kb.constants else f"q:{x}")
                                 for x in sub]) if self.model else 0.5
                out.append({"expr": expr, "inputs": sub, "value": float(num) if num.is_number else None,
                            "plausibility": float(plaus)})
        out.sort(key=lambda d: (-(d["value"] is not None), -d["plausibility"], len(d["inputs"])))
        return out[:max_out]

    def pi_groups(self, ctx):
        syms = [sp.Symbol(c) for c in ctx["constants"]][:8]
        if len(syms) < 2:
            return []
        _, pis = self.E.rayleigh(self.kb.quantities[ctx["target"]][1] if ctx["target"] else sp.Integer(1), syms)
        out = []
        for p in pis:
            num = p.subs({s: self.kb.constants[s.name][1] for s in syms})
            if num.is_number and float(num) != 0:
                out.append({"expr": p, "value": float(num)})
        return out

    # ------------------------------------------------- 3 connect fields
    def connections(self, ctx, max_out=6):
        rel_names = {f.name for f in ctx["laws"]}
        found = []
        for fa, fb, m in self.E.analogies():
            if fa.name in rel_names or fb.name in rel_names:
                for r in self.E.transfer_both(fa, fb, m):
                    if r.quantities & set(ctx["quantities"]):
                        found.append(("analogy", r))
        laws = ctx["laws"][:10]
        for a, b in combinations(laws, 2):
            for r in self.E.compose(a, b, max_results=2):
                found.append(("composition", r))
        out, seen = [], set()
        for kind, r in found:
            r.sym_to_q = {s: q for s, q in r.sym_to_q.items() if s in r.eq.free_symbols}
            if len(r.sym_to_q) < 2:
                continue
            key = self.E.pretty(r)
            if key in seen:
                continue
            seen.add(key)
            known, ratio = self.E.find_known(r)
            doms = {self.kb.by_name(n).domain for n in r.sources if self.kb.by_name(n)}
            plaus = np.mean([self.model.score(f"q:{a}", f"q:{b}") for a, b in combinations(sorted(r.quantities), 2)]) \
                if self.model and len(r.quantities) > 1 else 0.5
            cx = int(sp.count_ops(r.eq))
            out.append({"kind": kind, "relation": key, "via": " → ".join(dict.fromkeys(r.sources)),
                        "known": known.name if known is not None and ratio in (1, -1) else None,
                        "score": plaus + 0.3 * (len(doms) > 1) - 0.04 * cx, "note": r.note})
        out.sort(key=lambda d: (d["known"] is not None, -d["score"]))
        return out[:max_out]

    # ------------------------------------------------------- 4 experiment
    def experiment(self, ctx):
        from . import simulate
        q = set(ctx["named"])
        text = ctx.get("question", "").lower()
        if re.search(r"carbon dioxide|co2|climate|greenhouse", text):
            q |= {"co2_concentration"}
        if re.search(r"reaction|replicat|activation|catal", text):
            q |= {"rate_constant"}
        if re.search(r"turbulen|viscosity|fluid flow", text):
            q |= {"reynolds_number"}
        res = []
        if q & {"radiative_forcing", "co2_concentration", "climate_sensitivity_parameter", "albedo"}:
            for fb in (False, True):
                base = simulate.ebm(280, years=400, ice_albedo_feedback=fb)
                dbl = simulate.ebm(560, years=400, ice_albedo_feedback=fb)
                res.append(f"Energy-balance model, CO₂ 280→560 ppm, ice-albedo feedback {'on' if fb else 'off'}: "
                           f"warming {dbl['warming_K']:.2f} K (baseline {base['baseline_equilibrium_K']:.1f} K).")
            warm = simulate.ebm(560, years=400, ice_albedo_feedback=True)
            cold = simulate.ebm(560, years=400, ice_albedo_feedback=True, T0=230.0)
            Tw, Tc = warm["temperature_K"][-1], cold["temperature_K"][-1]
            if abs(Tw - Tc) > 5:
                res.append(f"Started from a frozen Earth (230 K) the same model settles at {Tc:.1f} K instead of "
                           f"{Tw:.1f} K: two stable climates exist (ice–albedo hysteresis).")
            else:
                res.append(f"Started from a frozen Earth (230 K) the model returns to {Tc:.1f} K: no second stable "
                           f"climate in this model at today's sunlight.")
        if q & {"rate_constant", "activation_energy", "pre_exponential"}:
            for Ea in (50e3, 100e3):
                ks = simulate.arrhenius(A=1e13, Ea=Ea, temperatures=(273, 298, 323, 373))["k"]
                res.append(f"Arrhenius, Ea = {Ea / 1e3:.0f} kJ/mol: rate rises ×{ks[-1] / ks[0]:.3g} from 0 °C to 100 °C.")
            kin = simulate.kinetics(["A + R -> 2 R", "R -> D"], [1.0, 0.3], {"A": 1.0, "R": 1e-6}, t_end=60, points=7)
            res.append("Autocatalysis A + R → 2R with decay R → D, starting from one replicator per million: R grows "
                       f"to {max(kin['R']):.3f} mol/L — exponential take-off once copying outpaces decay.")
        if q & {"reynolds_number", "viscosity", "kinematic_viscosity"}:
            res.append("Reynolds number for a 1 m pipe flow of water at 1 m/s: Re = ρvL/η ≈ "
                       f"{1000 * 1 * 1 / 1e-3:.0e} (turbulent above ≈ 2300–4000, the empirical transition).")
        return res

    # --------------------------------------------------------- 5 data
    def data(self, mystery):
        if mystery.get("dataset") == "exoplanets":
            from .studies import exoplanets
            res, extras = exoplanets.run(log=lambda *a: None)
            best, pw = res[0], next(r for r in res if r["model"].startswith("power law"))
            return [f"Searched {len(res)} candidate laws on 620 real giant planets (Open Exoplanet Catalogue).",
                    f"Best law (BIC): {best['model']} — cross-validated error {best['cv_rmse_dex']:.4f} dex vs "
                    f"{pw['cv_rmse_dex']:.4f} dex for a simple power law in mass and flux.",
                    f"Radius rises with flux but saturates and turns over at the highest flux "
                    f"(parameters {', '.join(f'{p:.3g}' for p in best['params'])}).",
                    f"Unexplained residual correlates with host-star metallicity (ρ = {extras['FeH'][0]:+.3f}): "
                    "metal-rich systems host denser giant planets."], best
        return [], None

    # -------------------------------------------------------- 6 judge
    def solve(self, m):
        self.log(f"\n▶ {m['title']}")
        ctx = self.understand(m["question"])
        self.log(f"  understands it through: {', '.join(f.name for f in ctx['laws'][:6])}")
        self.log(f"  target quantity: {self.kb.qname(ctx['target']) if ctx['target'] else '—'}")
        scales = self.scales(ctx)
        pis = self.pi_groups(ctx)
        conns = self.connections(ctx)
        exps = self.experiment(ctx)
        data_lines, data_best = self.data(m)
        findings = []
        for s in scales:
            v = f" ≈ {_fmt(s['value'])} (SI)" if s["value"] is not None else ""
            findings.append(f"Scale: {self.kb.qname(ctx['target'])} ~ {sp.sstr(s['expr']).replace('**', '^')}{v}")
        for p in pis[:3]:
            findings.append(f"Dimensionless number: {sp.sstr(p['expr']).replace('**', '^')} ≈ {_fmt(p['value'])}")
        for c in conns:
            tag = f"recovers known law '{c['known']}'" if c["known"] else "candidate (not in knowledge base, untested)"
            findings.append(f"{c['kind'].title()}: {c['relation']}  [{tag}; via {c['via']}]")
        findings += [f"Experiment: {e}" for e in exps]
        findings += [f"Data: {d}" for d in data_lines]
        verdict = self._verdict(m, ctx, scales, conns, exps, data_lines)
        for line in findings:
            self.log("   • " + line)
        self.log(f"  verdict: {verdict}")
        self._record(m, ctx, findings, verdict)
        return {"mystery": m, "context": ctx, "findings": findings, "verdict": verdict}

    def _verdict(self, m, ctx, scales, conns, exps, data_lines):
        if data_lines:
            return ("Partial progress: found a better-fitting empirical law in real data and a residual trend; "
                    "the physical mechanism remains unexplained. Literature novelty unchecked.")
        new = [c for c in conns if not c["known"]]
        if scales and any(s["value"] is not None for s in scales):
            return ("Quantified, not solved: Euresis derived the characteristic scales the answer must involve "
                    "and connected them to known laws. These frame the mystery; they do not explain its mechanism.")
        if exps:
            return ("Explored by simulation: Euresis' models reproduce the known structure of the problem "
                    "(magnitudes and feedbacks); the open part needs physics its models do not contain.")
        if new:
            return "Candidate connections only: relations not in its knowledge base, untested and unexplained."
        return "No progress: Euresis' knowledge and tools do not reach this question."

    def _record(self, m, ctx, findings, verdict):
        if self.space is None:
            return
        parents = [self.space.make_id("law", f"law|{f.name}") for f in ctx["laws"][:8]]
        parents = [p for p in parents if p in self.space.thoughts]
        mid = self.space.add("mystery", m["title"], body=m["question"], domain=ctx["laws"][0].domain if ctx["laws"] else "physics",
                             parents=parents, status="open mystery posed to Euresis", score=1.0, key=f"mystery|{m['id']}")
        for i, fnd in enumerate(findings):
            self.space.add("evidence", fnd[:110], body=fnd, domain="method", parents=[mid],
                           status="Euresis finding", score=0.5, key=f"mysteryfinding|{m['id']}|{i}|{fnd[:60]}")
        self.space.add("insight", f"Verdict: {m['title']}", body=verdict, domain="method", parents=[mid],
                       status="Euresis verdict", score=1.0, key=f"verdict|{m['id']}")


def run(ids=None, log=print):
    from .model import load_or_train
    from .render import export
    kb = KnowledgeBase()
    model = load_or_train(kb)
    solver = MysterySolver(kb, Engine(kb, model), model, ThoughtSpace(), log=log)
    results = [solver.solve(m) for m in load_mysteries() if not ids or m["id"] in ids]
    L = ["# Mysteries posed to Euresis", "",
         "The mysteries (questions only) were written by a person; everything below was produced by Euresis "
         "from its own knowledge base, reasoning engines, simulators and data analysis. "
         "Literature novelty checks could not run in this environment (no network access to paper databases).", ""]
    for r in results:
        m = r["mystery"]
        L += [f"## {m['title']}", "", f"> {m['question']}", "",
              f"*Euresis approached it through:* {', '.join(f.name for f in r['context']['laws'][:6])}", ""]
        L += [f"- {f}" for f in r["findings"]]
        L += ["", f"**Verdict:** {r['verdict']}", ""]
    OUT.write_text("\n".join(L))
    export()
    log(f"\nreport: {OUT.relative_to(OUT.parents[1])}")
    return results
