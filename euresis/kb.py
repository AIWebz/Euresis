"""Euresis knowledge base: loads, parses and dimension-checks all science."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property

import sympy as sp

from .dimensions import D, Dim, DIMENSIONLESS
from pathlib import Path

from .knowledge.constants import CONSTANTS
from .knowledge.formulas import _FORMULAS, _MATH_AND_PRINCIPLES
from .knowledge.formulas_ext import CONSTANTS_EXT, FORMULAS_EXT, PRINCIPLES_EXT, QUANTITIES_EXT
from .knowledge.quantities import QUANTITIES

USER_DIR = Path(__file__).resolve().parent / "knowledge" / "user"


def user_knowledge() -> dict[str, list[str]]:
    """Knowledge fed in later (``euresis learn``): one item per line, typed by prefix.

    formula   | domain | name | equation | sym:quantity ...
    principle | domain | name | statement
    quantity  | id | name | dimension
    constant  | symbol | name | value | unit | dimension
    frontier  | domain | problem | tags
    """
    out = {k: [] for k in ("formula", "principle", "quantity", "constant", "frontier")}
    if not USER_DIR.exists():
        return out
    for f in sorted(USER_DIR.glob("*.txt")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            kind, _, rest = line.partition("|")
            kind = kind.strip().lower()
            if kind in out:
                out[kind].append(rest.strip())
    return out

FUNCS = {"sqrt": sp.sqrt, "exp": sp.exp, "log": sp.log, "sin": sp.sin,
         "cos": sp.cos, "tan": sp.tan, "pi": sp.pi}

# Quantities that are specialisations of a more general family. Composition
# may identify members of the same family (e.g. a weight *is* a force).
FAMILY = {
    "mass1": "mass", "mass2": "mass",
    "charge1": "charge", "charge2": "charge",
    "weight": "force", "normal_force": "force", "friction_force": "force",
    "tension": "force", "buoyant_force": "force", "drag_force": "force",
    "kinetic_energy": "energy", "potential_energy": "energy", "work": "energy",
    "heat": "energy", "internal_energy": "energy", "rest_energy": "energy",
    "photon_energy": "energy", "binding_energy": "energy", "energy_level": "energy",
    "work_function": "energy",
    "initial_velocity": "velocity", "final_velocity": "velocity",
    "escape_velocity": "velocity", "orbital_velocity": "velocity",
    "recession_velocity": "velocity",
    "centripetal_acceleration": "acceleration",
    "gravitational_acceleration": "acceleration",
    "radius": "distance", "semi_major_axis": "distance",
    "schwarzschild_radius": "distance",
    "emf": "voltage", "electric_potential": "voltage",
    "heat_flow": "power", "luminosity": "power",
    "thrust": "force", "centripetal_force": "force",
    "terminal_velocity": "velocity", "drift_velocity": "velocity", "exhaust_velocity": "velocity",
    "source_velocity": "velocity",
    "hill_radius": "distance", "roche_limit": "distance", "photon_sphere_radius": "distance",
    "isco_radius": "distance", "impact_parameter": "distance", "curvature_radius": "distance",
    "jeans_mass": "mass", "chandrasekhar_mass": "mass", "initial_mass": "mass", "final_mass": "mass",
    "particle_mass": "mass", "reduced_mass": "mass",
    "zero_point_energy": "energy", "threshold_energy": "energy", "fermi_energy": "energy",
    "reaction_energy": "energy", "barrier_energy": "energy", "gamow_energy": "energy",
    "helmholtz_energy": "energy", "total_enthalpy": "energy",
    "plasma_frequency": "angular_frequency", "observed_frequency": "frequency",
    "sampling_frequency": "frequency", "noise_voltage": "voltage",
    "reactance": "resistance", "impedance": "resistance",
    "critical_density": "density", "particle_density": "density", "primary_density": "density",
    "satellite_density": "density", "crust_density": "density", "mantle_density": "density",
    "free_fall_time": "time", "stellar_lifetime": "time", "lifespan": "time",
    "heat_flux": "flux",
}


def family(qid: str) -> str:
    return FAMILY.get(qid, qid)


class DimensionError(ValueError):
    pass


def dim_of(expr: sp.Expr, dims: dict[sp.Symbol, Dim]) -> Dim:
    """Dimension of a SymPy expression; raises DimensionError if inhomogeneous."""
    if expr.is_Symbol:
        if expr not in dims:
            raise DimensionError(f"unknown symbol {expr}")
        return dims[expr]
    if expr.is_Number or expr in (sp.pi, sp.E) or expr.is_NumberSymbol:
        return DIMENSIONLESS
    if expr.is_Mul:
        out = DIMENSIONLESS
        for a in expr.args:
            out = out * dim_of(a, dims)
        return out
    if expr.is_Pow:
        base, ex = expr.args
        bd = dim_of(base, dims)
        if ex.is_Number:
            return bd ** sp.Rational(ex)
        if not bd.dimensionless or not dim_of(ex, dims).dimensionless:
            raise DimensionError(f"non-numeric exponent on dimensional base in {expr}")
        return DIMENSIONLESS
    if expr.is_Add:
        ds = [dim_of(a, dims) for a in expr.args]
        if any(d != ds[0] for d in ds):
            raise DimensionError(f"adding unlike dimensions in {expr}: {[str(d) for d in ds]}")
        return ds[0]
    if isinstance(expr, sp.Function):
        for a in expr.args:
            if not dim_of(a, dims).dimensionless:
                raise DimensionError(f"{expr.func} of a dimensional argument: {a}")
        return DIMENSIONLESS
    raise DimensionError(f"cannot analyse {expr!r}")


@dataclass
class Formula:
    name: str
    domain: str
    text: str
    eq: sp.Eq                      # in canonical symbols
    sym_to_q: dict                 # canonical Symbol -> quantity id
    constants: set                 # constant symbols used
    display: dict = field(default_factory=dict)  # canonical Symbol -> short Symbol
    holdout: bool = False

    @property
    def quantities(self) -> set[str]:
        return set(self.sym_to_q.values())

    @property
    def families(self) -> set[str]:
        return {family(q) for q in self.sym_to_q.values()}

    def pretty(self) -> str:
        return pretty_eq(self.eq, self.display)


@dataclass
class Principle:
    name: str
    domain: str
    statement: str


def pretty_eq(eq, display: dict) -> str:
    e = eq.subs(display, simultaneous=True) if display else eq
    s = f"{sp.sstr(e.lhs)} = {sp.sstr(e.rhs)}"
    for a, b in (("**", "^"), ("sqrt", "√"), ("pi", "π"), ("epsilon_0", "ε₀"),
                 ("mu_0", "μ₀"), ("hbar", "ħ"), ("k_B", "k_B"), ("sigma", "σ")):
        s = s.replace(a, b)
    return s


class KnowledgeBase:
    def __init__(self, exclude: set[str] | None = None):
        self.exclude = set(exclude or ())
        self.user = user_knowledge()
        qtab = dict(QUANTITIES)
        for line in QUANTITIES_EXT.strip().splitlines() + self.user["quantity"]:
            q, name, spec = (x.strip() for x in line.split("|"))
            qtab.setdefault(q, (name, spec))
        self.quantities = {q: (name, D(spec)) for q, (name, spec) in qtab.items()}
        self.constants = {**CONSTANTS, **CONSTANTS_EXT}
        for line in self.user["constant"]:
            sym, name, val, unit, spec = (x.strip() for x in line.split("|"))
            self.constants.setdefault(sym, (name, float(val), unit, spec, False))
        self.const_syms = {k: sp.Symbol(k) for k in self.constants}
        self.dims: dict[sp.Symbol, Dim] = {self.const_syms[k]: D(v[3]) for k, v in self.constants.items()}
        self.display_sym: dict[str, sp.Symbol] = {}
        self.formulas: list[Formula] = []
        self.held_out: list[Formula] = []
        self.principles: list[Principle] = []
        for q, (_, d) in self.quantities.items():
            self.dims[sp.Symbol(q)] = d
        self._load()

    # ------------------------------------------------------------- loading
    def _load(self):
        lines = _FORMULAS.strip().splitlines() + FORMULAS_EXT.strip().splitlines() + self.user["formula"]
        seen = set()
        self.errors: list[str] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if parts[1] in seen:
                continue
            seen.add(parts[1])
            domain, name, text = parts[0], parts[1], parts[2]
            mapping = dict(tok.split(":") for tok in parts[3].split()) if len(parts) > 3 and parts[3] else {}
            try:
                f = self._parse(domain, name, text, mapping)
            except (KeyError, DimensionError, SyntaxError, TypeError, ValueError) as e:
                self.errors.append(f"{name}: {e}")
                continue
            if name in self.exclude:
                f.holdout = True
                self.held_out.append(f)
            else:
                self.formulas.append(f)
        for line in (_MATH_AND_PRINCIPLES.strip().splitlines() + PRINCIPLES_EXT.strip().splitlines()
                     + self.user["principle"]):
            domain, name, statement = (p.strip() for p in line.split("|", 2))
            self.principles.append(Principle(name, domain, statement))

    def _parse(self, domain, name, text, mapping) -> Formula:
        lhs, rhs = text.split("=")
        idents = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", text))
        local, sym_to_q, display, consts = {}, {}, {}, set()
        counts: dict[str, int] = {}
        for s in mapping.values():
            counts[s] = counts.get(s, 0) + 1
        for ident in idents:
            if ident in FUNCS:
                local[ident] = FUNCS[ident]
            elif ident in mapping:
                q = mapping[ident]
                if q not in self.quantities:
                    raise KeyError(f"{name}: unknown quantity {q}")
                canon = sp.Symbol(q if counts[q] == 1 else f"{q}__{ident}")
                self.dims[canon] = self.quantities[q][1]
                local[ident] = canon
                sym_to_q[canon] = q
                self._display(q, ident)
                display[canon] = sp.Symbol(ident.rstrip("_") or ident)
            elif ident in self.const_syms:
                local[ident] = self.const_syms[ident]
                consts.add(self.const_syms[ident])
            else:
                raise KeyError(f"{name}: symbol '{ident}' is neither mapped nor a constant")
        eq = sp.Eq(sp.sympify(lhs, locals=local), sp.sympify(rhs, locals=local), evaluate=False)
        dl, dr = dim_of(eq.lhs, self.dims), dim_of(eq.rhs, self.dims)
        if dl != dr:
            raise DimensionError(f"{name}: LHS [{dl}] != RHS [{dr}]")
        return Formula(name, domain, text, eq, sym_to_q, consts, display)

    def _display(self, q: str, ident: str) -> sp.Symbol:
        if q not in self.display_sym:
            taken = {s.name for s in self.display_sym.values()}
            nm = ident.rstrip("_") or ident
            if nm in taken or nm in self.const_syms:
                nm = f"{nm}_{q.split('_')[0]}"
            self.display_sym[q] = sp.Symbol(nm)
        return self.display_sym[q]

    # ------------------------------------------------------------- queries
    def display_map(self, syms) -> dict:
        out = {}
        for s in syms:
            q = s.name.split("__")[0]
            if q in self.display_sym:
                out[s] = self.display_sym[q]
            elif q in self.quantities:
                out[s] = sp.Symbol(q)
        return out

    def qname(self, q: str) -> str:
        return self.quantities[q][0] if q in self.quantities else q

    def by_name(self, name: str) -> Formula | None:
        for f in self.formulas + self.held_out:
            if f.name.lower() == name.lower():
                return f
        return None

    @cached_property
    def domains(self) -> list[str]:
        return sorted({f.domain for f in self.formulas} | {p.domain for p in self.principles})

    def documents(self) -> list[tuple[str, str, str]]:
        """(kind, title, text) for every item — the training corpus."""
        docs = []
        for f in self.formulas:
            qn = ", ".join(self.qname(q) for q in sorted(f.quantities))
            cn = ", ".join(self.constants[c.name][0] for c in f.constants)
            docs.append(("formula", f.name, f"{f.name}. {f.domain}. {f.pretty()}. relates {qn}. {cn}"))
        for p in self.principles:
            docs.append(("principle", p.name, f"{p.name}. {p.domain}. {p.statement}"))
        for k, (n, v, u, d, ex) in self.constants.items():
            docs.append(("constant", n, f"{n} ({k}) = {v:.10g} {u}{' (exact)' if ex else ''}"))
        return docs

    def stats(self) -> dict:
        return {"formulas": len(self.formulas), "held_out": len(self.held_out),
                "principles": len(self.principles), "constants": len(self.constants),
                "quantities": len(self.quantities), "domains": len(self.domains)}
