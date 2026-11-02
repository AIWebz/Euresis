"""Lay out the Thought Space and export it as a self-contained infinite canvas."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .space import KINDS, SPACE_DIR, load_records

GOLDEN = math.pi * (3 - math.sqrt(5))

DOMAIN_ORDER = ["mathematics", "method", "information", "physics", "mechanics", "gravitation",
                "relativity", "quantum", "atomic", "nuclear", "astrophysics", "astronomy",
                "electromagnetism", "circuits", "waves", "optics", "thermodynamics",
                "statistical_mechanics", "fluids", "materials", "earth_science", "chemistry", "biology"]


class Grid:
    """Occupancy grid so that thoughts never overlap, however many there are."""

    def __init__(self, cell=150):
        self.cell, self.used = cell, set()

    def place(self, x, y):
        c = self.cell
        gx, gy = round(x / c), round(y / c)
        if (gx, gy) not in self.used:
            self.used.add((gx, gy))
            return gx * c, gy * c
        for r in range(1, 400):
            best = None
            for dx in range(-r, r + 1):
                for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    if (gx + dx, gy + dy) not in self.used:
                        d = (gx + dx - x / c) ** 2 + (gy + dy - y / c) ** 2
                        if best is None or d < best[0]:
                            best = (d, gx + dx, gy + dy)
            if best:
                self.used.add((best[1], best[2]))
                return best[1] * c, best[2] * c
        return x, y


def layout(thoughts: dict[str, dict]) -> dict[str, tuple[float, float]]:
    pos: dict[str, tuple[float, float]] = {}
    grid = Grid()
    doms = [t for t in thoughts.values() if t["kind"] == "domain"]
    order = {d: i for i, d in enumerate(DOMAIN_ORDER)}
    doms.sort(key=lambda t: order.get(t["domain"], 99))
    R = 3600
    hub = {}
    for i, t in enumerate(doms):
        a = 2 * math.pi * i / len(doms) - math.pi / 2
        hub[t["domain"]] = (R * math.cos(a), R * math.sin(a))
        pos[t["id"]] = grid.place(*hub[t["domain"]])
    # constants of nature at the centre
    consts = [t for t in thoughts.values() if t["kind"] == "constant"]
    for i, t in enumerate(consts):
        r = 170 * math.sqrt(i + 1)
        pos[t["id"]] = grid.place(r * math.cos(i * GOLDEN), r * math.sin(i * GOLDEN))
    # knowledge in sunflower spirals around each field's hub
    per_dom: dict[str, int] = {}
    for t in thoughts.values():
        if t["kind"] in ("law", "principle"):
            d = t["domain"]
            k = per_dom.get(d, 0) + 1
            per_dom[d] = k
            hx, hy = hub.get(d, (0, 0))
            r = 165 * math.sqrt(k)
            pos[t["id"]] = grid.place(hx + r * math.cos(k * GOLDEN), hy + r * math.sin(k * GOLDEN))
    # frontier problems on the outer rim
    fr = [t for t in thoughts.values() if t["kind"] == "frontier"]
    for i, t in enumerate(fr):
        a = 2 * math.pi * (i + 0.5) / max(1, len(fr)) - math.pi / 2
        pos[t["id"]] = grid.place(7600 * math.cos(a), 7600 * math.sin(a))
    # everything Euresis thought of: near its parents, pushed outward by generation
    rest = sorted((t for t in thoughts.values() if t["id"] not in pos), key=lambda t: (t["cycle"], t["t"]))
    for t in rest:
        ps = [pos[p] for p in t["parents"] if p in pos]
        if ps:
            x = sum(p[0] for p in ps) / len(ps)
            y = sum(p[1] for p in ps) / len(ps)
        else:
            x, y = 0.0, 0.0
        r = math.hypot(x, y) or 1.0
        push = {"analogy": 1.12, "hypothesis": 1.28, "scale": 1.0, "derivation": 1.3,
                "rederivation": 1.18, "dimensional": 1.33, "prediction": 1.45, "question": 1.4,
                "insight": 1.0}.get(t["kind"], 1.25)
        tx, ty = x * push, y * push
        if t["kind"] == "scale":
            tx, ty = x * 0.6 + 900 * math.cos(len(pos)), y * 0.6 + 900 * math.sin(len(pos))
        if t["kind"] == "insight":
            tx, ty = x * 0.5, y * 0.5 - 400
        pos[t["id"]] = grid.place(tx, ty)
    return pos


def export(space_path: Path | None = None, out: Path | None = None, benchmark: Path | None = None) -> Path:
    space_path = space_path or SPACE_DIR / "thoughts.jsonl"
    out = out or SPACE_DIR / "space.html"
    thoughts = load_records(space_path)
    pos = layout(thoughts)
    nodes = []
    for t in thoughts.values():
        x, y = pos[t["id"]]
        nodes.append({"id": t["id"], "k": t["kind"], "ti": t["title"], "b": t.get("body", ""),
                      "f": t.get("formula", ""), "d": t.get("domain", ""), "s": t.get("status", ""),
                      "c": t.get("cycle", 0), "sc": t.get("score", 0), "x": round(x), "y": round(y),
                      "p": [p for p in t["parents"] if p in pos]})
    bench = None
    bp = benchmark or SPACE_DIR / "benchmark.json"
    if Path(bp).exists():
        bench = json.loads(Path(bp).read_text())
    data = {"nodes": nodes, "kinds": KINDS, "bench": bench}
    tpl = (Path(__file__).parent / "templates" / "space.html").read_text()
    out.write_text(tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False)))
    return out
