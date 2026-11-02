"""Euresis reasoning engine: symbolic manipulation of the laws of nature.

Capabilities
------------
* solve / evaluate any known formula for any variable
* dimensional analysis (Rayleigh's method + Buckingham Π groups)
* composition — eliminate a shared quantity between two laws to derive a new one
* structural analogy — find laws with identical mathematical form in different
  fields and transfer knowledge across the analogy
* equivalence testing up to a dimensionless constant (novelty / verification)
"""
from __future__ import annotations

import signal
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import permutations

import sympy as sp

from .dimensions import Dim
from .kb import DimensionError, Formula, KnowledgeBase, dim_of, family, pretty_eq


class _Timeout(Exception):
    pass


@contextmanager
def time_limit(seconds: float):
    """Abort runaway symbolic manipulation (SymPy can stall on rare inputs)."""
    def handler(signum, frame):
        raise _Timeout()
    try:
        old = signal.signal(signal.SIGALRM, handler)
    except ValueError:          # not in main thread: run without a limit
        yield
        return
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@dataclass
class Relation:
    eq: sp.Eq
    sym_to_q: dict
    constants: set
    method: str
    sources: list = field(default_factory=list)
    note: str = ""
    target: sp.Symbol | None = None

    @property
    def quantities(self):
        return set(self.sym_to_q.values())

    @property
    def families(self):
        return frozenset(family(q) for q in self.sym_to_q.values())


def _as_relation(f: Formula) -> Relation:
    return Relation(f.eq, dict(f.sym_to_q), set(f.constants), "known", [f.name])


class Engine:
    def __init__(self, kb: KnowledgeBase, model=None):
        self.kb = kb
        self.model = model
        self._index: dict[frozenset, list[Formula]] = {}
        for f in kb.formulas:
            self._index.setdefault(frozenset(f.families), []).append(f)

    # ---------------------------------------------------------------- basics
    def pretty(self, rel) -> str:
        syms = rel.eq.free_symbols - set(rel.constants)
        return pretty_eq(rel.eq, self.kb.display_map(syms))

    def check_dims(self, eq: sp.Eq) -> bool:
        if not isinstance(eq, sp.Equality):
            return False
        try:
            return dim_of(eq.lhs, self.kb.dims) == dim_of(eq.rhs, self.kb.dims)
        except DimensionError:
            return False

    def solve_for(self, rel, sym: sp.Symbol) -> list[sp.Expr]:
        try:
            sols = sp.solve(sp.Eq(rel.eq.lhs, rel.eq.rhs), sym, dict=False)
        except (NotImplementedError, TypeError, ValueError):
            return []
        sols = [s for s in sols if not s.has(sp.I)] or sols
        # prefer the physically meaningful (non-negative) root first
        def key(s):
            c = s.as_coeff_Mul()[0]
            return 0 if (c.is_number and c > 0) else 1
        return sorted(sols, key=key)

    def evaluate(self, rel, target_q: str, values: dict[str, float]) -> float | None:
        """Numerically evaluate `target_q` given SI values for the other quantities."""
        tsym = next((s for s, q in rel.sym_to_q.items() if q == target_q), None)
        if tsym is None:
            return None
        sols = self.solve_for(rel, tsym)
        if not sols:
            return None
        subs = {sp.Symbol(k): v[1] for k, v in self.kb.constants.items()}
        for s, q in rel.sym_to_q.items():
            if q in values:
                subs[s] = values[q]
        val = sols[0].subs(subs).evalf()
        return float(val) if val.is_real else None

    # ---------------------------------------------------- dimensional analysis
    def rayleigh(self, target_dim: Dim, inputs: list[sp.Symbol]):
        """Find exponents a_i with Π inputs_i^a_i having dimension target_dim.

        Returns (exponents | None, pi_groups) where pi_groups are the
        dimensionless combinations (Buckingham Π theorem)."""
        A = sp.Matrix([[self.kb.dims[s][k] for s in inputs] for k in range(7)])
        b = sp.Matrix([target_dim[k] for k in range(7)])
        null = A.nullspace()
        pis = []
        for v in null:
            v = v * sp.lcm([sp.fraction(x)[1] for x in v])
            pis.append(sp.Mul(*[s ** e for s, e in zip(inputs, v)]))
        try:
            sol, params = A.gauss_jordan_solve(b)
        except ValueError:
            return None, pis
        if params.shape[0]:
            sol = sol.subs({p: 0 for p in params})
        return [sp.nsimplify(x) for x in sol], pis

    def monomial(self, inputs, exps) -> sp.Expr:
        return sp.Mul(*[s ** e for s, e in zip(inputs, exps)])

    # ------------------------------------------------------------- composition
    def compose(self, a, b, max_results=4, seconds=3.0) -> list[Relation]:
        out: list[Relation] = []
        try:
            with time_limit(seconds):
                self._compose(a, b, max_results, out)
        except _Timeout:
            pass
        return out

    def _compose(self, a: Formula | Relation, b: Formula | Relation, max_results, out) -> list[Relation]:
        ra = a if isinstance(a, Relation) else _as_relation(a)
        rb = b if isinstance(b, Relation) else _as_relation(b)
        fam_a: dict[str, list] = {}
        fam_b: dict[str, list] = {}
        for s, q in ra.sym_to_q.items():
            fam_a.setdefault(family(q), []).append(s)
        for s, q in rb.sym_to_q.items():
            fam_b.setdefault(family(q), []).append(s)
        shared = [f for f in fam_a if f in fam_b and len(fam_a[f]) == 1 and len(fam_b[f]) == 1]
        if sp.count_ops(ra.eq) > 30 or sp.count_ops(rb.eq) > 30:
            return out
        for elim in shared:
            sa, sb = fam_a[elim][0], fam_b[elim][0]
            # identify the other shared quantities (same family -> same thing);
            # where one side has several members (m1, m2) try each identification
            base = {fam_b[g][0]: fam_a[g][0] for g in shared if g != elim}
            variants = [base]
            for g in fam_a:
                  if g == elim or g not in fam_b or g in shared:
                      continue
                  if len(fam_b[g]) == 1:
                      variants = [{**v, fam_b[g][0]: x} for v in variants for x in fam_a[g]][:4]
                  elif len(fam_a[g]) == 1:
                      variants = [{**v, y: fam_a[g][0]} for v in variants for y in fam_b[g]][:4]
            for ident in variants:
                eqb = rb.eq.subs(ident, simultaneous=True) if ident else rb.eq
                for sol in self.solve_for(ra, sa)[:1]:
                    if not isinstance(eqb, sp.Equality):
                        continue
                    expr = sp.simplify(eqb.lhs.subs(sb, sol) - eqb.rhs.subs(sb, sol))
                    if expr == 0 or expr.free_symbols <= set(ra.constants) | set(rb.constants):
                        continue
                    s2q = {}
                    for s in expr.free_symbols:
                        if s in ra.sym_to_q:
                            s2q[s] = ra.sym_to_q[s]
                        elif s in rb.sym_to_q:
                            s2q[s] = rb.sym_to_q[s]
                    if len(s2q) < 2:
                        continue
                    consts = {s for s in expr.free_symbols if s not in s2q}
                    # choose a target: B's subject if it survived, else A's subject
                    cands = [x for x in (rb.eq.lhs, ra.eq.lhs) if isinstance(x, sp.Symbol) and x in s2q]
                    target = cands[0] if cands else sorted(s2q, key=str)[0]
                    sols = self.solve_for(Relation(sp.Eq(expr, 0), s2q, consts, ""), target)
                    if not sols:
                        continue
                    if sp.count_ops(sols[0]) > 30:
                        continue
                    eq = sp.Eq(target, sp.simplify(sols[0]))
                    if not self.check_dims(eq):
                        continue
                    note = f"eliminated {self.kb.qname(elim)}"
                    if ident:
                        note += "; identified " + ", ".join(
                            f"{self.kb.qname(rb.sym_to_q[k])} ≡ {self.kb.qname(ra.sym_to_q[v])}" for k, v in ident.items())
                    out.append(Relation(eq, s2q, consts, "composition",
                                        ra.sources + rb.sources, note, target))
                    if len(out) >= max_results:
                        return out
        return out

    # ---------------------------------------------------------------- analogy
    def signature(self, f: Formula):
        """Canonical structural form, invariant to renaming of variables."""
        syms = sorted(f.eq.free_symbols - f.constants, key=str)
        if not 2 <= len(syms) <= 5:
            return None, None
        K = sp.Symbol("K")
        csub = {c: K for c in f.constants}
        best, best_map = None, None
        for perm in permutations(range(len(syms))):
            sub = {s: sp.Symbol(f"x{perm[i]}") for i, s in enumerate(syms)}
            sub.update(csub)
            e = f.eq.subs(sub, simultaneous=True)
            s = sp.srepr(sp.Eq(e.lhs, e.rhs))
            if best is None or s < best:
                best, best_map = s, {v.name: k for k, v in sub.items() if k in syms}
        return best, best_map

    def analogies(self, min_ops=3):
        groups: dict[str, list] = {}
        for f in self.kb.formulas:
            if len(f.eq.free_symbols) == len(f.constants):
                continue
            ops = sp.count_ops(f.eq.rhs) + sp.count_ops(f.eq.lhs)
            sig, m = self.signature(f)
            if sig is None or ops < min_ops:
                continue
            groups.setdefault(sig, []).append((f, m))
        pairs = []
        for sig, members in groups.items():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    (fa, ma), (fb, mb) = members[i], members[j]
                    if fa.domain == fb.domain:
                        continue
                    sym_map = {ma[k]: mb[k] for k in ma}
                    ca, cb = sorted(fa.constants, key=str), sorted(fb.constants, key=str)
                    if len(ca) == len(cb):
                        sym_map.update(dict(zip(ca, cb)))
                    pairs.append((fa, fb, sym_map))
        return pairs

    def transfer(self, fa: Formula, fb: Formula, sym_map: dict) -> list[Relation]:
        """Carry laws from fa's field into fb's field across a structural analogy."""
        qmap, fmap, cmap = {}, {}, {}
        for sa, sb in sym_map.items():
            if sa in fa.constants:
                cmap[sa] = sb
            else:
                qa, qb = fa.sym_to_q[sa], fb.sym_to_q[sb]
                if qa != qb:
                    qmap[qa] = qb
                    fmap[family(qa)] = family(qb)
        if not cmap and not fmap:
            return []
        out = []
        for g in self.kb.formulas:
            if g is fa or g.domain == fb.domain:
                continue
            if not (g.constants <= set(cmap)):
                continue
            gq = g.quantities
            n_mapped = len([q for q in gq if q in qmap or family(q) in fmap])
            if n_mapped < (1 if g.constants else 2):
                continue
            sub, s2q, unresolved = {}, {}, []
            for s, q in g.sym_to_q.items():
                if q in qmap:
                    nq = qmap[q]
                elif family(q) in fmap:
                    tgt = fmap[family(q)]
                    suffix = q[len(q.rstrip("0123456789")):]
                    nq = next((x for x in (tgt + suffix, tgt) if x in self.kb.quantities), q)
                else:
                    nq = q
                ns = sp.Symbol(nq)
                sub[s], s2q[ns] = ns, nq
                if q not in qmap and family(q) not in fmap and family(q) not in {"distance", "length", "time", "velocity", "energy", "force", "power"}:
                    unresolved.append(ns)
            sub.update(cmap)
            eq = g.eq.subs(sub, simultaneous=True)
            if not isinstance(eq, sp.Equality):
                continue
            # repair: if dimensions fail, re-type the subject using the model
            if not self.check_dims(eq) and isinstance(eq.lhs, sp.Symbol):
                try:
                    need = dim_of(eq.rhs, self.kb.dims)
                except DimensionError:
                    continue
                cands = [q for q, (_, d) in self.kb.quantities.items() if d == need]
                if not cands:
                    continue
                ctx = [f"q:{q}" for q in s2q.values() if sp.Symbol(q) != eq.lhs] + [f"c:{c}" for c in cmap.values()]
                orig = g.sym_to_q.get(g.eq.lhs, "")
                best = max(cands, key=lambda q: self._ctx_score(q, ctx) + self._name_sim(q, orig))
                ns = sp.Symbol(best)
                s2q.pop(eq.lhs, None)
                s2q[ns] = best
                eq = sp.Eq(ns, eq.rhs)
            if not self.check_dims(eq) or len(unresolved) > 1 or not self._nontrivial(eq):
                continue
            consts = {c for c in eq.free_symbols if c.name in self.kb.constants}
            s2q = {s: q for s, q in s2q.items() if s in eq.free_symbols}
            out.append(Relation(eq, s2q, consts, "analogy", [fa.name, fb.name, g.name],
                                f"{g.name} transferred via {fa.name} ↔ {fb.name}",
                                eq.lhs if isinstance(eq.lhs, sp.Symbol) else None))
        return out

    @staticmethod
    def _nontrivial(eq) -> bool:
        if not isinstance(eq, sp.Equality) or not isinstance(eq.lhs, sp.Symbol):
            return isinstance(eq, sp.Equality)
        rhs_q = [x for x in eq.rhs.free_symbols if "_" not in x.name or len(x.name) > 8]
        return eq.lhs not in eq.rhs.free_symbols and len(eq.rhs.free_symbols) >= 1 and bool(rhs_q or eq.rhs.free_symbols)

    def transfer_both(self, fa, fb, sym_map):
        inv = {v: k for k, v in sym_map.items()}
        return self.transfer(fa, fb, sym_map) + self.transfer(fb, fa, inv)

    def _name_sim(self, a, b) -> float:
        wa, wb = set(self.kb.qname(a).split()), set(self.kb.qname(b).split())
        return 1.2 * len(wa & wb) / max(1, len(wa | wb))

    def _ctx_score(self, q, ctx):
        if self.model is None:
            return 0.0
        return sum(self.model.score(f"q:{q}", c) for c in ctx) / max(1, len(ctx))

    # ----------------------------------------------------- novelty/equivalence
    CANON = None

    def _canon_consts(self, eq):
        """Rewrite derived constants in terms of more basic ones (ħ = h/2π, ...)."""
        if Engine.CANON is None:
            S = sp.Symbol
            Engine.CANON = {S("hbar"): S("h") / (2 * sp.pi), S("k_e"): 1 / (4 * sp.pi * S("epsilon_0")),
                            S("R"): S("N_A") * S("k_B"), S("F_c"): S("N_A") * S("e")}
        return eq.subs(Engine.CANON)

    def equivalent(self, r1, r2):
        try:
            with time_limit(2.0):
                return self._equivalent(r1, r2)
        except _Timeout:
            return None

    def _equivalent(self, r1, r2):
        """Is r1 the same law as r2 up to a dimensionless constant factor?

        Returns the factor (r2-subject / r1-subject) or None."""
        r1 = r1 if isinstance(r1, Relation) else _as_relation(r1)
        r2 = r2 if isinstance(r2, Relation) else _as_relation(r2)
        if r1.constants != r2.constants:
            e1c, e2c = self._canon_consts(r1.eq), self._canon_consts(r2.eq)
            if not isinstance(e1c, sp.Equality) or not isinstance(e2c, sp.Equality):
                return None
            c1 = {x for x in e1c.free_symbols if x.name in self.kb.constants}
            c2 = {x for x in e2c.free_symbols if x.name in self.kb.constants}
            if c1 != c2:
                return None
            r1 = Relation(e1c, r1.sym_to_q, c1, r1.method)
            r2 = Relation(e2c, r2.sym_to_q, c2, r2.method)
        s1, s2 = dict(r1.sym_to_q), dict(r2.sym_to_q)
        pairing, left1 = {}, []
        used = set()
        for a, qa in s1.items():
            m = [b for b, qb in s2.items() if b not in used and qb == qa] or \
                [b for b, qb in s2.items() if b not in used and family(qb) == family(qa)]
            if len(m) >= 1:
                pairing[a] = m[0]
                used.add(m[0])
            else:
                left1.append(a)
        left2 = [b for b in s2 if b not in used]
        for a in list(left1):
            m = [b for b in left2 if self.kb.dims[b] == self.kb.dims[a]]
            if len(m) == 1:
                pairing[a] = m[0]
                left2.remove(m[0])
                left1.remove(a)
        if left1 or left2:
            return None
        e1 = r1.eq.subs(pairing, simultaneous=True)
        target = r2.eq.lhs if isinstance(r2.eq.lhs, sp.Symbol) and r2.eq.lhs in s2 else next(iter(s2))
        a = self.solve_for(Relation(e1, s2, r1.constants, ""), target)
        b = self.solve_for(r2, target)
        for x in a:
            for y in b:
                if y == 0:
                    continue
                ratio = sp.simplify(y / x)
                if not (ratio.free_symbols & set(s2)) and not (ratio.free_symbols - set()):
                    return ratio
        return None

    def find_known(self, rel: Relation, pool=None):
        """Best-matching known law: exact (factor ±1) preferred over 'same form'."""
        best = (None, None)
        cands = self._index.get(rel.families, []) if pool is None else pool
        for f in cands:
            r = self.equivalent(rel, f)
            if r is None:
                continue
            if r in (1, -1):
                return f, r
            if best[0] is None:
                best = (f, r)
        return best
