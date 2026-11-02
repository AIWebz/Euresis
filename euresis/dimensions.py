"""SI dimensional analysis.

Every physical quantity is a vector of rational exponents over the seven SI
base dimensions: mass, length, time, electric current, temperature, amount of
substance, luminous intensity.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Iterable

BASE = ("M", "L", "T", "I", "Θ", "N", "J")


class Dim(tuple):
    """Immutable dimension vector, e.g. force = Dim(M=1, L=1, T=-2)."""

    def __new__(cls, *args, **kw):
        if args and len(args) == 1 and isinstance(args[0], Iterable) and not kw:
            vals = tuple(Fraction(x) for x in args[0])
        else:
            vals = tuple(Fraction(kw.get(b, 0)) for b in ("M", "L", "T", "I", "K", "N", "J"))
        if len(vals) != 7:
            raise ValueError("dimension needs 7 components")
        return super().__new__(cls, vals)

    def __mul__(self, other: "Dim") -> "Dim":
        return Dim(a + b for a, b in zip(self, other))

    def __truediv__(self, other: "Dim") -> "Dim":
        return Dim(a - b for a, b in zip(self, other))

    def __pow__(self, p) -> "Dim":
        p = Fraction(p)
        return Dim(a * p for a in self)

    @property
    def dimensionless(self) -> bool:
        return all(a == 0 for a in self)

    def __str__(self) -> str:
        if self.dimensionless:
            return "1"
        parts = []
        for b, a in zip(BASE, self):
            if a == 0:
                continue
            parts.append(b if a == 1 else f"{b}^{a}")
        return "·".join(parts)


def D(spec: str) -> Dim:
    """Parse a compact spec like 'M L2 T-2' or 'I T' or '1'."""
    spec = spec.strip()
    if spec in ("", "1"):
        return Dim()
    kw = {}
    for tok in spec.split():
        sym = tok[0]
        exp = tok[1:] or "1"
        key = {"Θ": "K", "K": "K"}.get(sym, sym)
        kw[key] = Fraction(exp)
    return Dim(**kw)


DIMENSIONLESS = Dim()
