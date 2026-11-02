"""The Thought Space — an unbounded, append-only memory of every thought.

Each thought is one JSON line in ``space/thoughts.jsonl``. Nothing is ever
deleted; new thoughts link to the thoughts they were built from, so the space
is a growing graph of knowledge → reasoning → discovery with no size limit.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

SPACE_DIR = Path(__file__).resolve().parent.parent / "space"

KINDS = {
    "domain": "Field of science",
    "law": "Established law / formula",
    "principle": "Established principle",
    "constant": "Constant of nature",
    "analogy": "Structural analogy",
    "derivation": "Derived relation",
    "rederivation": "Re-derived known law",
    "hypothesis": "Hypothesis",
    "dimensional": "Dimensional-analysis result",
    "scale": "Natural scale",
    "prediction": "Verified prediction",
    "question": "Open question",
    "frontier": "Frontier problem",
    "insight": "Insight",
}


class ThoughtSpace:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else SPACE_DIR / "thoughts.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.thoughts: dict[str, dict] = {}
        if self.path.exists():
            self.thoughts = load_records(self.path)

    @staticmethod
    def make_id(kind: str, key: str) -> str:
        return f"{kind}:{hashlib.sha1(key.encode()).hexdigest()[:10]}"

    def add(self, kind, title, body="", formula="", domain="", parents=(), status="",
            score=0.0, cycle=0, key=None, **meta) -> str:
        tid = self.make_id(kind, key or f"{title}|{formula}")
        if tid in self.thoughts:
            t = self.thoughts[tid]
            new_parents = [p for p in parents if p not in t["parents"] and p != tid]
            if new_parents:
                t["parents"].extend(new_parents)
                self._append({"id": tid, "_update": True, "parents": t["parents"]})
            return tid
        t = {"id": tid, "kind": kind, "title": title, "body": body, "formula": formula,
             "domain": domain, "parents": [p for p in parents if p != tid], "status": status,
             "score": round(float(score), 4), "cycle": cycle, "t": time.time(), **meta}
        self.thoughts[tid] = t
        self._append(t)
        return tid

    def _append(self, rec):
        with self.path.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def reload(self):
        self.__init__(self.path)

    def by_kind(self, kind):
        return [t for t in self.thoughts.values() if t["kind"] == kind]

    def stats(self) -> dict:
        out = {}
        for t in self.thoughts.values():
            out[t["kind"]] = out.get(t["kind"], 0) + 1
        out["total"] = len(self.thoughts)
        out["links"] = sum(len(t["parents"]) for t in self.thoughts.values())
        return out


def load_records(path: Path) -> dict[str, dict]:
    out = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("_update"):
            out[r["id"]]["parents"] = r["parents"]
        else:
            out[r["id"]] = r
    return out
