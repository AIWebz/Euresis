"""The claims registry — one database for everything Euresis asserts.

Every candidate discovery (a theorem, a formula, a law, an orbit…) is stored as a
*claim* with its exact machine-checkable payload. A claim's status can only be
changed by the verification gate (``gate.py``):

    candidate          → recorded, not yet checked
    proved             → a formal/rigorous proof succeeded (Z3, Lean, interval arithmetic)
    verified-numeric   → checked to high precision but NOT proved
    refuted            → a verifier found it false
    unverified         → no verifier could decide (timeout, tool unavailable)

Novelty is tracked separately (``novelty`` field): whether it is new is a
different question from whether it is true.

The database is SQLite at ``data/registry.db`` (machine-local). Every write also
exports ``space/claims.json`` — the committed, human-readable source of truth from
which the database is rebuilt on a fresh machine.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "registry.db"
EXPORT = ROOT / "space" / "claims.json"

STATUSES = ("candidate", "proved", "verified-numeric", "refuted", "unverified")
KINDS = ("inequality", "z3", "identity", "constant", "orbit", "lean", "physics-relation", "music", "game",
         "empirical")

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    statement   TEXT NOT NULL,
    payload     TEXT NOT NULL,
    source      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'candidate',
    verifier    TEXT,
    evidence    TEXT,
    novelty     TEXT NOT NULL DEFAULT 'not checked',
    created     REAL NOT NULL,
    updated     REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,
    args        TEXT NOT NULL,
    state       TEXT NOT NULL DEFAULT 'queued',
    result      TEXT,
    error       TEXT,
    attempts    INTEGER NOT NULL DEFAULT 0,
    created     REAL NOT NULL,
    started     REAL,
    finished    REAL
);
CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state);
"""


def claim_id(kind: str, payload: dict) -> str:
    """Content address: the same claim always gets the same id."""
    blob = json.dumps({"kind": kind, "payload": payload}, sort_keys=True)
    return kind[:3] + "-" + hashlib.sha256(blob.encode()).hexdigest()[:12]


class Registry:
    def __init__(self, path: Path | str = DB_PATH, export: Path | str | None = EXPORT):
        self.path = Path(path)
        self.export_path = Path(export) if export else None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not self.path.exists()
        with self._conn() as c:
            c.executescript(SCHEMA)
        if fresh and self.export_path and self.export_path.exists():
            self.load_export()

    @contextmanager
    def _conn(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ----------------------------------------------------------- claims
    def add(self, kind: str, statement: str, payload: dict, source: str, novelty: str | None = None) -> str:
        if kind not in KINDS:
            raise ValueError(f"unknown claim kind {kind!r}; expected one of {KINDS}")
        cid = claim_id(kind, payload)
        now = time.time()
        with self._conn() as c:
            row = c.execute("SELECT id FROM claims WHERE id=?", (cid,)).fetchone()
            if row is None:
                c.execute("INSERT INTO claims (id, kind, statement, payload, source, novelty, created, updated) "
                          "VALUES (?,?,?,?,?,?,?,?)",
                          (cid, kind, statement, json.dumps(payload, sort_keys=True), source,
                           novelty or "not checked", now, now))
            elif novelty:
                c.execute("UPDATE claims SET novelty=?, updated=? WHERE id=?", (novelty, now, cid))
        self._export()
        return cid

    def set_status(self, cid: str, status: str, verifier: str, evidence: dict | str):
        """Only the verification gate should call this."""
        if status not in STATUSES:
            raise ValueError(status)
        ev = evidence if isinstance(evidence, str) else json.dumps(evidence, sort_keys=True, default=str)
        with self._conn() as c:
            n = c.execute("UPDATE claims SET status=?, verifier=?, evidence=?, updated=? WHERE id=?",
                          (status, verifier, ev, time.time(), cid)).rowcount
        if not n:
            raise KeyError(cid)
        self._export()

    def set_novelty(self, cid: str, novelty: str):
        with self._conn() as c:
            c.execute("UPDATE claims SET novelty=?, updated=? WHERE id=?", (novelty, time.time(), cid))
        self._export()

    def get(self, cid: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM claims WHERE id=?", (cid,)).fetchone()
        return self._row(r) if r else None

    def claims(self, status: str | None = None, kind: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM claims WHERE 1=1", []
        if status:
            q += " AND status=?"
            args.append(status)
        if kind:
            q += " AND kind=?"
            args.append(kind)
        with self._conn() as c:
            return [self._row(r) for r in c.execute(q + " ORDER BY created", args)]

    def stats(self) -> dict:
        with self._conn() as c:
            rows = c.execute("SELECT status, COUNT(*) n FROM claims GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        if d.get("evidence"):
            try:
                d["evidence"] = json.loads(d["evidence"])
            except json.JSONDecodeError:
                pass
        return d

    # ------------------------------------------------------------ export
    def _export(self):
        if not self.export_path:
            return
        data = self.claims()
        for d in data:
            d.pop("created", None)
            d.pop("updated", None)
        self.export_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.export_path.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True, default=str) + "\n")
        os.replace(tmp, self.export_path)          # atomic: readers (e.g. git) never see a half-written file

    def load_export(self):
        data = json.loads(self.export_path.read_text())
        now = time.time()
        with self._conn() as c:
            for d in data:
                ev = d.get("evidence")
                c.execute("INSERT OR REPLACE INTO claims (id, kind, statement, payload, source, status, verifier, "
                          "evidence, novelty, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (d["id"], d["kind"], d["statement"], json.dumps(d["payload"], sort_keys=True), d["source"],
                           d["status"], d.get("verifier"),
                           None if ev is None else (ev if isinstance(ev, str) else json.dumps(ev, sort_keys=True)),
                           d.get("novelty", "not checked"), now, now))

    # -------------------------------------------------------------- jobs
    def submit(self, kind: str, args: dict) -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO jobs (kind, args, created) VALUES (?,?,?)",
                            (kind, json.dumps(args, sort_keys=True), time.time()))
            return cur.lastrowid

    def claim_job(self) -> dict | None:
        """Atomically take the oldest queued job."""
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            r = c.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY id LIMIT 1").fetchone()
            if r is None:
                return None
            c.execute("UPDATE jobs SET state='running', started=?, attempts=attempts+1 WHERE id=?",
                      (time.time(), r["id"]))
        d = dict(r)
        d["args"] = json.loads(d["args"])
        return d

    def finish_job(self, jid: int, result=None, error: str | None = None):
        with self._conn() as c:
            c.execute("UPDATE jobs SET state=?, result=?, error=?, finished=? WHERE id=?",
                      ("failed" if error else "done", json.dumps(result, default=str) if result is not None else None,
                       error, time.time(), jid))

    def requeue_stale(self, older_than_s: float = 6 * 3600) -> int:
        """Jobs left 'running' by a worker that died (e.g. container restart) go back to the queue."""
        with self._conn() as c:
            return c.execute("UPDATE jobs SET state='queued' WHERE state='running' AND started < ?",
                             (time.time() - older_than_s,)).rowcount

    def jobs(self, state: str | None = None) -> list[dict]:
        q = "SELECT * FROM jobs" + (" WHERE state=?" if state else "") + " ORDER BY id"
        with self._conn() as c:
            rows = c.execute(q, (state,) if state else ()).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["args"] = json.loads(d["args"])
            out.append(d)
        return out
