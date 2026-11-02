"""The Euresis explorer: builds on established science to find new relations.

Every step is written into the Thought Space with links to what it was built
from, so the full chain of reasoning behind each result can be traced.

Strategies, in order of each cycle:
  1. Structural analogy   — laws with identical mathematical form in different
                            fields; carry other laws across the analogy.
  2. Natural scales       — dimensional analysis on sets of fundamental constants
                            (Planck units, couplings, atomic scales...).
  3. Gap questions        — the trained concept model predicts links between
                            quantities that no known law connects; Euresis asks
                            the question and attempts a dimensional answer.
  4. Dimensional sweep    — for each quantity, the most plausible scaling law
                            from model-chosen inputs (Rayleigh's method).
  5. Composition          — eliminate shared quantities between pairs of laws
                            (including laws Euresis derived in earlier cycles).
  6. Prediction           — evaluate new relations on real systems (Earth, Sun,
                            pendulum...) and compare with measured values.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from itertools import combinations

import numpy as np
import sympy as sp

from .dimensions import D
from .engine import Engine, Relation, _Timeout, _as_relation, time_limit
from .kb import KnowledgeBase, family
from .knowledge import frontier as frontier_mod
from .space import ThoughtSpace

# Reference measurements used to test predictions (SI units).
SCENARIOS = [
    # name, target family, inputs {family: (value, label)}, measured, source
    ("Earth: escape speed from the surface", "velocity",
     {"mass": "M_earth", "distance": "R_earth"}, 11_186.0, "measured, NASA Earth fact sheet"),
    ("Earth: speed of a low circular orbit", "velocity",
     {"mass": "M_earth", "distance": "R_earth"}, 7_905.0, "measured, NASA Earth fact sheet"),
    ("Earth: surface gravitational acceleration", "acceleration",
     {"mass": "M_earth", "distance": "R_earth"}, 9.798, "measured (equatorial, gravitational part)"),
    ("Earth: orbital speed around the Sun", "velocity",
     {"mass": "M_sun", "distance": "AU"}, 29_780.0, "measured"),
    ("Earth: orbital period around the Sun", "period",
     {"mass": "M_sun", "distance": "AU"}, 3.155_8e7, "sidereal year"),
    ("Sun: Schwarzschild radius", "distance", {"mass": "M_sun"}, 2_953.3, "GR textbook value"),
    ("1 m pendulum on Earth: period", "period",
     {"length": 1.0, "acceleration": "g_n"}, 2.006, "measured"),
]

SCALE_SETS = [
    ("Planck scales", ["G", "hbar", "c", "k_B"], ["L", "T", "M", "M L2 T-2", "K"]),
    ("Gravitational radius of a mass", ["G", "c", "mass"], ["L"]),
    ("Compton scale of a mass", ["hbar", "c", "mass"], ["L"]),
    ("Atomic scales", ["hbar", "m_e", "e", "epsilon_0"], ["L", "M L2 T-2", "T"]),
    ("Electromagnetic coupling", ["e", "epsilon_0", "hbar", "c"], []),
    ("Gravitational coupling of the proton", ["G", "hbar", "c", "m_p"], []),
    ("Thermal de Broglie wavelength", ["hbar", "mass", "k_B", "temperature"], ["L"]),
    ("Cosmological scales", ["c", "G", "H_0"], ["L", "T", "M L-3"]),
]
SCALE_QUANTITY = {"L": "distance", "T": "time", "M": "mass", "M L2 T-2": "energy",
                  "K": "temperature", "M L-3": "density"}
DIM_NAMES = {"L": "length", "T": "time", "M": "mass", "M L2 T-2": "energy",
             "K": "temperature", "M L-3": "density"}


DIRECTIVE = ("Discover relations that are not yet part of established knowledge. Build on the laws "
             "you were given and on your own verified results; prefer bridges between different fields; "
             "check every candidate for dimensional consistency and against measurements; never "
             "present an untested candidate as established fact.")


def _fmt(x: float) -> str:
    return f"{x:.4g}" if 1e-3 <= abs(x) < 1e5 else f"{x:.4e}"


class Explorer:
    def __init__(self, kb: KnowledgeBase, engine: Engine, model, space: ThoughtSpace | None,
                 seed: int = 1, log=print):
        self.kb, self.E, self.model, self.space = kb, engine, model, space
        self.rng = random.Random(seed)
        self.log = log
        self.law_id: dict[str, str] = {}
        self.const_id: dict[str, str] = {}
        self.dom_id: dict[str, str] = {}
        self.frontier_ids: list[tuple[str, list[str]]] = []
        self.relations: list[tuple[Relation, str]] = []   # derived relations + thought id
        self.seen: set[str] = set()
        self.results: list[dict] = []                      # everything found (for benchmark)
        self.cycle = 0
        self._tried: set = set()
        self._composed_from: set = set()
        self.candidates: list[dict] = []      # ranked candidate discoveries
        self._cand_index: dict = {}
        self.directive_id = None

    # ---------------------------------------------------------------- helpers
    def _add(self, *a, **kw):
        if self.space is None:
            return f"tmp:{len(self.results)}:{self.rng.random()}"
        return self.space.add(*a, cycle=self.cycle, **kw)

    def _parents_for(self, rel: Relation) -> list[str]:
        ps = [self.law_id[n] for n in rel.sources if n in self.law_id]
        ps += [self.const_id[c.name] for c in rel.constants if c.name in self.const_id]
        return list(dict.fromkeys(ps))

    def _domain_of(self, rel: Relation) -> str:
        doms = [self.kb.by_name(n).domain for n in rel.sources if self.kb.by_name(n)]
        return doms[0] if doms else "physics"

    def _plausibility(self, quantities, constants=()) -> float:
        nodes = [f"q:{q}" for q in quantities] + [f"c:{c}" for c in constants]
        pairs = list(combinations(nodes, 2))
        if not pairs or self.model is None:
            return 0.5
        return float(np.mean([self.model.score(a, b) for a, b in pairs]))

    def _key(self, rel: Relation) -> str:
        fam = {s: sp.Symbol(family(q)) for s, q in rel.sym_to_q.items()}
        try:
            with time_limit(2.0):
                e = rel.eq.subs(fam, simultaneous=True)
                return sp.srepr(sp.simplify(e.lhs - e.rhs))
        except (_Timeout, Exception):
            return str(rel.eq)

    def _link_frontier(self, tid, quantities, constants):
        tags = {f"q:{q}" for q in quantities} | {f"q:{family(q)}" for q in quantities} | \
               {f"c:{c}" for c in constants}
        for fid, ftags in self.frontier_ids:
            if len(tags & set(ftags)) >= 2 and self.space is not None:
                self.space.thoughts[fid]["parents"].append(tid) if tid not in self.space.thoughts[fid]["parents"] else None

    def _record(self, rel: Relation, kind_new="derivation", extra_parents=()):
        """Verify a relation against known science and store it."""
        rel.sym_to_q = {x: q for x, q in rel.sym_to_q.items() if x in rel.eq.free_symbols}
        rel.constants = {x for x in rel.constants if x in rel.eq.free_symbols}
        if len(rel.sym_to_q) < 2:
            return None
        key = self._key(rel)
        if key in self.seen:
            return None
        self.seen.add(key)
        known, ratio = self.E.find_known(rel)
        quantities = rel.quantities
        consts = [c.name for c in rel.constants]
        plaus = self._plausibility(quantities, consts)
        doms = {self.kb.by_name(n).domain for n in rel.sources if self.kb.by_name(n)}
        score = plaus + 0.25 * (len(doms) > 1) + 0.15 / max(1, len(quantities) - 1)
        parents = self._parents_for(rel) + list(extra_parents)
        pretty = self.E.pretty(rel)
        result = {"relation": rel, "pretty": pretty, "known": known.name if known else None,
                  "ratio": ratio, "score": score, "method": rel.method}
        self.results.append(result)
        if known is not None and ratio in (1, -1):
            kind, status = "rederivation", "consistent with known law"
            body = f"Euresis re-derived {known.name} ({rel.note})" + (" — sign convention differs" if ratio == -1 else "")
            parents.append(self.law_id.get(known.name, ""))
        elif known is not None:
            kind, status = kind_new, "same form as known law, different coefficient"
            body = f"{rel.note}. Same variables as {known.name}, differs by factor {ratio}."
            parents.append(self.law_id.get(known.name, ""))
        else:
            kind = kind_new
            doms_all = {self.kb.by_name(n).domain for n in set(rel.sources) if self.kb.by_name(n)}
            depth = len(dict.fromkeys(rel.sources))
            cx = int(sp.count_ops(rel.eq.rhs)) + int(sp.count_ops(rel.eq.lhs))
            # near-duplicate of an earlier candidate (same law up to a constant)?
            fam = rel.families
            dup = next((c for c in self._cand_index.get(fam, [])
                        if self.E.equivalent(rel, c["relation"]) is not None), None)
            if dup is not None:
                return None
            # novelty: plausible, simple, short chains that genuinely connect fields
            novelty = (plaus + 0.3 * min(2, max(0, len(doms_all) - 1))
                       - 0.05 * max(0, cx - 6) - 0.12 * max(0, depth - 3)
                       + 0.15 / max(1, len(quantities) - 1))
            score = novelty
            result["score"] = score
            result["complexity"] = cx
            result["depth"] = depth
            self._cand_index.setdefault(fam, []).append(result)
            if len(doms_all) >= 2:
                status = (f"candidate discovery · bridges {', '.join(sorted(d.replace('_', ' ') for d in doms_all))}"
                          " · not in knowledge base · untested")
            else:
                status = "new to Euresis · dimensionally consistent · untested"
            body = rel.note + (". Derivation chain: " + " → ".join(dict.fromkeys(rel.sources)) if rel.sources else "")
            result["domains"] = sorted(doms_all)
            self.candidates.append(result)
        tid = self._add(kind, pretty if kind != "rederivation" else f"Re-derived: {known.name}",
                        body=body, formula=pretty, domain=self._domain_of(rel),
                        parents=[p for p in parents if p], status=status, score=score,
                        method=rel.method, key=f"{kind}|{key}")
        result["id"] = tid
        if kind != "rederivation" and not known and result.get("complexity", 0) <= 12 \
                and result.get("depth", 0) <= 5 and len(quantities) <= 4:
            self.relations.append((rel, tid))
            self._link_frontier(tid, quantities, consts)
        self._predict(rel, tid)
        return result

    # ----------------------------------------------------------------- seeding
    def seed(self):
        """Lay down the foundation: every field, law, principle and constant."""
        self.directive_id = self._add("insight", "Directive: discover what we don't know yet", body=DIRECTIVE,
                                      domain="method", status="standing goal", score=1.0, key="directive")
        for d in self.kb.domains:
            self.dom_id[d] = self._add("domain", d.replace("_", " ").title(), domain=d,
                                       body=f"Field of science: {d}", key=f"domain|{d}")
        for k, (n, v, u, dspec, exact) in self.kb.constants.items():
            self.const_id[k] = self._add("constant", n, formula=f"{k} = {v:.10g} {u}", domain="constants",
                                         status="exact (SI definition)" if exact else "CODATA 2018",
                                         key=f"constant|{k}")
        for f in self.kb.formulas:
            ps = [self.dom_id[f.domain]] + [self.const_id[c.name] for c in f.constants]
            self.law_id[f.name] = self._add("law", f.name, formula=f.pretty(), domain=f.domain,
                                            parents=ps, status="established",
                                            body="Relates " + ", ".join(self.kb.qname(q) for q in sorted(f.quantities)),
                                            key=f"law|{f.name}")
        for p in self.kb.principles:
            dom = p.domain if p.domain in self.dom_id else p.domain
            if dom not in self.dom_id:
                self.dom_id[dom] = self._add("domain", dom.title(), domain=dom, key=f"domain|{dom}")
            self._add("principle", p.name, body=p.statement, domain=dom, parents=[self.dom_id[dom]],
                      status="established", key=f"principle|{p.name}")
        for dom, prob, tags in frontier_mod.load():
            fid = self._add("frontier", prob, domain=dom, status="unsolved",
                            parents=[self.dom_id.get(dom, "")] if dom in self.dom_id else [],
                            body="Open problem at the edge of current science.", key=f"frontier|{prob}")
            self.frontier_ids.append((fid, tags))

    # --------------------------------------------------------------- analogies
    def explore_analogies(self):
        n = 0
        for fa, fb, sym_map in self.E.analogies():
            mapping = ", ".join(
                f"{self.kb.qname(fa.sym_to_q[a]) if a in fa.sym_to_q else a} ↔ "
                f"{self.kb.qname(fb.sym_to_q[b]) if b in fb.sym_to_q else b}"
                for a, b in sym_map.items())
            aid = self._add("analogy", f"{fa.name} ≅ {fb.name}",
                            body=f"Identical mathematical structure across {fa.domain} and {fb.domain}: {mapping}",
                            formula=f"{fa.pretty()}   ≅   {fb.pretty()}", domain=fb.domain,
                            parents=[self.law_id[fa.name], self.law_id[fb.name]], status="structural match",
                            score=self._plausibility(fa.quantities | fb.quantities), key=f"analogy|{fa.name}|{fb.name}")
            for rel in self.E.transfer_both(fa, fb, sym_map):
                r = self._record(rel, kind_new="hypothesis", extra_parents=[aid])
                n += r is not None
        self.log(f"  analogies: {len(self.E.analogies())} structural matches, {n} transferred laws")

    # ----------------------------------------------------------- natural scales
    def explore_scales(self):
        for label, names, targets in SCALE_SETS:
            syms, values, parents = [], {}, []
            for nme in names:
                s = sp.Symbol(nme)
                syms.append(s)
                if nme in self.kb.constants:
                    values[s] = self.kb.constants[nme][1]
                    parents.append(self.const_id[nme])
            sid = None
            for tgt in targets:
                exps, pis = self.E.rayleigh(D(tgt), syms)
                if exps is None:
                    continue
                expr = self.E.monomial(syms, exps)
                txt = self.E.pretty(Relation(sp.Eq(sp.Symbol(f"{DIM_NAMES[tgt]}_scale"), expr), {}, set(), ""))
                num = expr.subs(values)
                val = f" ≈ {_fmt(float(num))} (SI)" if num.is_number else ""
                match = ""
                if num.is_number:
                    for ck, (cn, cv, cu, cd, _) in self.kb.constants.items():
                        if ck in names or D(cd) != D(tgt):
                            continue
                        g = sp.nsimplify(cv / float(num), [sp.pi], tolerance=2e-3)
                        if len(str(g)) <= 14 and g != 0:
                            match = f" Matches the {cn}: {ck} = {g} × this scale."
                            parents = parents + [self.const_id[ck]]
                            break
                sid = self._add("scale", f"{label}: {DIM_NAMES[tgt]}", formula=txt + val,
                                body=f"Unique combination of {', '.join(names)} with dimension of {DIM_NAMES[tgt]} "
                                     f"(Rayleigh's method)." + match, domain="physics", parents=parents,
                                status="derived by dimensional analysis", score=0.9)
                tq = SCALE_QUANTITY[tgt]
                s2q = {x: x.name for x in syms if x.name in self.kb.quantities}
                s2q[sp.Symbol(tq)] = tq
                rel = Relation(sp.Eq(sp.Symbol(tq), expr), s2q,
                               {x for x in syms if x.name in self.kb.constants}, "dimensional", [], label)
                self.results.append({"relation": rel, "pretty": txt, "method": "scale", "id": sid})
                if len(s2q) > 1:
                    self._predict(rel, sid)
                self._link_frontier(sid, [n for n in names if n in self.kb.quantities],
                                    [n for n in names if n in self.kb.constants])
            for pi in pis:
                num = pi.subs(values)
                val = float(num) if num.is_number else None
                ident = ""
                alpha = self.kb.constants["alpha"][1]
                if val is not None:
                    for v, lab in ((val, "Π"), (1 / val, "1/Π")):
                        g = sp.nsimplify(v / alpha, [sp.pi], tolerance=1e-4)
                        if len(str(g)) <= 6:
                            ident = (f" {lab} = {g}·α — Euresis recovers the fine-structure constant "
                                     f"α ≈ 1/{1 / alpha:.3f}")
                            break
                txt = sp.sstr(pi).replace("**", "^")
                pid = self._add("scale", f"{label}: dimensionless group", formula=f"Π = {txt}" + (f" ≈ {_fmt(val)}" if val else ""),
                                body="Buckingham Π group — a pure number nature fixes." + ident,
                                domain="physics", parents=parents + ([sid] if sid else []),
                                status="dimensionless invariant", score=0.95)
                self._link_frontier(pid, [], [n for n in names if n in self.kb.constants])
        if self.space is None:
            return
        # cross-scale insight: how weak is gravity?
        G, hb, c, mp = (self.kb.constants[k][1] for k in ("G", "hbar", "c", "m_p"))
        a_g = G * mp ** 2 / (hb * c)
        a = self.kb.constants["alpha"][1]
        self._add("insight", "Gravity is ~10^36 times weaker than electromagnetism",
                  body=f"Comparing the two dimensionless couplings Euresis found: α ≈ {a:.5g} and "
                       f"α_G = G·m_p²/(ħc) ≈ {a_g:.3e}. Ratio α/α_G ≈ {a / a_g:.2e}. Explaining this "
                       f"ratio is the hierarchy problem.",
                  domain="physics", parents=[t for t in self.space.thoughts if t.startswith("scale:")][-4:] if self.space else [],
                  status="quantitative insight", score=1.0)
        self.log("  natural scales: Planck, atomic, Compton, gravitational, cosmological + couplings")

    # ------------------------------------------------------- dimensional sweep
    def _dims(self, name):
        return self.kb.dims[sp.Symbol(name)]

    def best_scaling(self, target: str, must_include: str | None = None, k: int = 7, top: int = 1):
        """Most plausible power law for `target` from model-chosen inputs."""
        if self.model is None or f"q:{target}" not in self.model.index:
            return None
        tdim = self.kb.quantities[target][1]
        cands = []
        for node, sc in self.model.related(f"q:{target}", k=40):
            nm = node[2:]
            if node.startswith("q:") and nm not in self.kb.quantities:
                continue
            if node.startswith("q:") and (family(nm) == family(target) or nm in FAMILY_SKIP):
                continue
            d = self._dims(nm)
            if d.dimensionless or d == tdim:
                continue
            if any(self._dims(c) == d for c, _ in cands):
                continue
            cands.append((nm, sc))
            if len(cands) >= k:
                break
        if must_include and must_include not in [c for c, _ in cands]:
            cands = [(must_include, self.model.score(f"q:{target}", f"q:{must_include}"))] + cands[: k - 1]
        found = []
        T = np.array([float(x) for x in tdim])
        for r in (2, 3):
            for sub in combinations(cands, r):
                names = [s for s, _ in sub]
                if must_include and must_include not in names:
                    continue
                A = np.array([[float(x) for x in self._dims(n)] for n in names]).T
                if np.linalg.matrix_rank(A) < r:
                    continue
                x, *_ = np.linalg.lstsq(A, T, rcond=None)
                if np.abs(A @ x - T).max() > 1e-9:
                    continue
                fr = [sp.nsimplify(round(v * 12) / 12) for v in x]
                if any(v == 0 for v in fr):
                    continue
                sc = float(np.mean([s for _, s in sub])) - 0.03 * r
                found.append((sc, names, fr))
        found.sort(key=lambda x: -x[0])
        return found[:top] if top > 1 else (found[0] if found else None)

    def explore_dimensional(self, targets=None, max_records=45):
        targets = targets or [q for q in self.kb.quantities if any(q in f.quantities for f in self.kb.formulas)]
        found = []
        for t in targets:
            for b in self.best_scaling(t, top=3) or []:
                found.append((b[0], t, b[1], b[2]))
        found.sort(key=lambda x: -x[0])
        found = [f for f in found if f[0] >= 0.55]
        n = 0
        for sc, t, names, exps in found:
            syms = [sp.Symbol(nm) for nm in names]
            expr = self.E.monomial(syms, exps)
            s2q = {s: s.name for s in syms if s.name in self.kb.quantities}
            ts = sp.Symbol(t)
            s2q[ts] = t
            consts = {s for s in syms if s.name in self.kb.constants}
            rel = Relation(sp.Eq(ts, expr), s2q, consts, "dimensional", [],
                           f"{self.kb.qname(t)} ∝ " + " · ".join(f"{self.kb.qname(nm)}^{e}" for nm, e in zip(names, exps))
                           + " (dimensionless prefactor undetermined)", ts)
            rel.sources = [f.name for f in self.kb.formulas if t in f.quantities][:2]
            r = self._record(rel, kind_new="dimensional")
            if r is not None:
                r["target"] = t
                n += 1
            if n >= max_records:
                break
        self.log(f"  dimensional analysis: {len(found)} scaling laws evaluated, {n} recorded")

    # ------------------------------------------------------------ gap questions
    def explore_gaps(self, top=10):
        if self.model is None:
            return
        cooc = set()
        for f in self.kb.formulas:
            for a, b in combinations(sorted({family(q) for q in f.quantities}), 2):
                cooc.add((a, b))
        qs = sorted({family(q) for f in self.kb.formulas for q in f.quantities})
        gaps = []
        for a, b in combinations(qs, 2):
            if (a, b) in cooc or a not in self.kb.quantities or b not in self.kb.quantities:
                continue
            if self._dims(a).dimensionless or self._dims(b).dimensionless:
                continue
            s = self.model.score(f"q:{a}", f"q:{b}")
            gaps.append((s, a, b))
        gaps.sort(reverse=True)
        n = 0
        for s, a, b in gaps[:top]:
            qid = self._add("question", f"How does {self.kb.qname(a)} depend on {self.kb.qname(b)}?",
                            body=f"The concept model rates this link {s:.2f} likely, yet no known law in the "
                                 f"knowledge base connects them.", domain="physics", status="open", score=s,
                            parents=[self.law_id[f.name] for f in self.kb.formulas if a in f.quantities][:1] +
                                    [self.law_id[f.name] for f in self.kb.formulas if b in f.quantities][:1])
            bsc = self.best_scaling(a, must_include=b)
            if bsc:
                _, names, exps = bsc
                syms = [sp.Symbol(nm) for nm in names]
                ts = sp.Symbol(a)
                s2q = {x: x.name for x in syms if x.name in self.kb.quantities}
                s2q[ts] = a
                rel = Relation(sp.Eq(ts, self.E.monomial(syms, exps)), s2q,
                               {x for x in syms if x.name in self.kb.constants}, "dimensional", [],
                               "candidate answer by dimensional analysis", ts)
                r = self._record(rel, kind_new="dimensional", extra_parents=[qid])
                n += r is not None
        self.log(f"  gap questions: {min(top, len(gaps))} asked, {n} candidate answers")

    # ------------------------------------------------------------- composition
    def explore_compositions(self, n_pairs=150):
        """Compose pairs of laws; newest discoveries are combined with known laws first."""
        known = [(_as_relation(f), self.law_id.get(f.name)) for f in self.kb.formulas]
        fresh = [r for r in self.relations if r[1] not in self._composed_from]
        if self.space is not None:
            fresh.sort(key=lambda r: -self.space.thoughts.get(r[1], {}).get("score", 0))
        fresh = fresh[:60]
        pool = known + self.relations
        cands = {}
        def consider(a, b, bonus):
            ra, rb = a[0], b[0]
            fa, fb = ra.families, rb.families
            shared = fa & fb
            if ra is rb or not shared or shared == fa or shared == fb:
                return
            k = (id(ra), id(rb)) if id(ra) < id(rb) else (id(rb), id(ra))
            if k in self._tried:
                return
            ext = (ra.quantities - rb.quantities) | (rb.quantities - ra.quantities)
            da = {self.kb.by_name(n).domain for n in ra.sources if self.kb.by_name(n)}
            db = {self.kb.by_name(n).domain for n in rb.sources if self.kb.by_name(n)}
            cross = 0.3 if da and db and not (da & db) else 0.0
            sc = self._plausibility(ext) + bonus + cross - 0.02 * len(ext)
            if k not in cands or sc > cands[k][0]:
                cands[k] = (sc, ra, rb)
        for a in fresh:
            for b in pool:
                consider(a, b, 0.35)
        for _ in range(4000):
            consider(*self.rng.sample(known, 2), 0.0)
        chosen = sorted(cands.items(), key=lambda kv: -kv[1][0])[:n_pairs]
        new = []
        for k, (_, ra, rb) in chosen:
            self._tried.add(k)
            for rel in self.E.compose(ra, rb, max_results=3):
                if len(rel.sym_to_q) > 5:
                    continue
                r = self._record(rel)
                if r is not None:
                    new.append(r)
        self._composed_from.update(r[1] for r in fresh)
        self.log(f"  compositions: {len(chosen)} pairs tried, {len(new)} new results "
                 f"({sum(1 for r in new if r['known'] and r['ratio'] in (1, -1))} re-derived known laws)")
        return new

    # -------------------------------------------------------------- prediction
    def _predict(self, rel: Relation, tid: str):
        for name, tfam, inputs, measured, src in SCENARIOS:
            tsyms = [s for s, q in rel.sym_to_q.items() if family(q) == tfam]
            if len(tsyms) != 1:
                continue
            ts = tsyms[0]
            others = {s: q for s, q in rel.sym_to_q.items() if s != ts}
            if sorted(family(q) for q in others.values()) != sorted(inputs):
                continue
            subs = {sp.Symbol(k): v[1] for k, v in self.kb.constants.items()}
            for s, q in others.items():
                v = inputs[family(q)]
                subs[s] = self.kb.constants[v][1] if isinstance(v, str) else v
            sols = [rel.eq.rhs] if rel.eq.lhs == ts else self.E.solve_for(rel, ts)
            pred = None
            for sol in sols:
                try:
                    val = complex(sol.subs(subs).evalf())
                except (TypeError, ValueError):
                    continue
                if abs(val.imag) <= 1e-9 * abs(val) and val.real > 0:
                    pred = val.real
                    break
            if pred is None:
                continue
            ratio = measured / pred
            if rel.method == "dimensional" and not (0.05 < ratio < 20):
                continue
            if rel.method == "dimensional":
                guess = sp.nsimplify(ratio, [sp.pi], tolerance=0.01)
                body = (f"Prediction {_fmt(pred)} vs measured {_fmt(measured)} ({src}). "
                        f"Calibrating against experiment fixes the undetermined prefactor C ≈ {ratio:.4g}"
                        + (f" ≈ {guess}" if len(str(guess)) < 12 else "") + ".")
                status = "prefactor calibrated by measurement"
            else:
                err = abs(pred - measured) / measured
                if err > 0.02:
                    continue
                body = f"Euresis predicts {_fmt(pred)}; measured value {_fmt(measured)} ({src}). Error {err * 100:.2f}%."
                status = "verified against measurement"
            pid = self._add("prediction", name, formula=f"{self.kb.qname(rel.sym_to_q[ts])} = {_fmt(pred)}",
                            body=body, domain=self._domain_of(rel), parents=[tid], status=status, score=1.0,
                            key=f"prediction|{name}|{tid}")
            self.results.append({"prediction": name, "value": pred, "measured": measured, "id": pid,
                                 "status": status})

    # ------------------------------------------------------------------ report
    def report(self, path, top=30):
        cands = sorted(self.candidates, key=lambda r: -r["score"])
        seen, rows = set(), []
        for r in cands:
            if r["pretty"] in seen:
                continue
            seen.add(r["pretty"])
            rows.append(r)
            if len(rows) >= top:
                break
        bridges = sum(1 for r in self.candidates if len(r.get("domains", [])) >= 2)
        L = ["# Euresis — candidate discoveries", "",
             f"> **Directive:** {DIRECTIVE}", "",
             f"{len(self.candidates)} relations were found that are not in Euresis' knowledge base; "
             f"{bridges} of them bridge two or more fields. The {len(rows)} highest-ranked are listed below.", "",
             "**How to read this.** Every candidate is dimensionally consistent and was derived step by step "
             "from established laws, so it is *true if its premises and identifications hold*. "
             "\"Not in the knowledge base\" is not the same as \"unknown to science\": many candidates "
             "will turn out to be known results or algebraic consequences, and the identifications "
             "Euresis makes (e.g. treating two masses as the same body) are assumptions. Each one needs a "
             "literature check and, where it makes a physical claim, an experiment.", "",
             "| # | Candidate relation | Fields bridged | Score | Built from |",
             "|---|---|---|---|---|"]
        for i, r in enumerate(rows, 1):
            rel = r["relation"]
            src = " → ".join(dict.fromkeys(rel.sources))
            L.append(f"| {i} | `{r['pretty']}` | {', '.join(r.get('domains', [])) or '—'} | "
                     f"{r['score']:.2f} | {src} |")
        L += ["", "Quantities: " + "; ".join(sorted({f"{self.E.pretty(r['relation'])}: "
                                                      + ", ".join(self.kb.qname(q) for q in sorted(r['relation'].quantities))
                                                      for r in rows[:10]}))]
        Path(path).write_text("\n".join(L) + "\n")
        return rows

    # ------------------------------------------------------------------ driver
    def run(self, cycles=3, seed_space=True, start=1):
        if seed_space:
            self.seed()
        for c in range(start, start + cycles):
            self.cycle = c
            self.log(f"cycle {c}")
            before = len(self.results)
            if c == start:
                self.explore_analogies()
                self.explore_scales()
                self.explore_gaps()
                self.explore_dimensional()
            self.explore_compositions()
            found = self.results[before:]
            novel = [r for r in found if "relation" in r and not r.get("known")]
            top = max(novel, key=lambda r: r.get("score", 0), default=None)
            if self.space is not None:
                self._add("insight", f"Cycle {c} summary",
                          body=f"{len(found)} results this cycle; {len(novel)} relations new to Euresis. "
                               + (f"Most promising: {top['pretty']}" if top else ""),
                          domain="physics", parents=[top["id"]] if top and "id" in top else [],
                          status="reflection", score=0.5, key=f"insight|cycle|{c}|{len(self.space.thoughts)}")
        return self.results


FAMILY_SKIP = {"number", "order", "turns"}
