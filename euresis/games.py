"""Game theory discovery: the complete solution of take-away games, proved.

An *octal game* 0.d1d2d3… is played on heaps of counters: on your turn you remove k
counters from one heap if digit d_k allows it — bit 1: the k counters are the whole
heap; bit 2: the rest stays as one heap; bit 4: the rest may be split into two
non-empty heaps. Whoever cannot move loses. By the Sprague–Grundy theorem, play on a
heap of size n is solved by its Grundy value G(n) (a position is lost iff the XOR of
its heaps' values is 0).

Euresis computes G(n) and looks for a repeating pattern. The **Guy–Smith periodicity
theorem** turns a finite check into a proof: if G(n + p) = G(n) for every n with
n0 ≤ n < 2·n0 + p + t (t = number of digits), then G(n + p) = G(n) for ALL n ≥ n0.
So each result "0.d1d2…: G is periodic with pre-period n0 and period p" is a theorem,
which completely solves the game for every heap size. The verification gate (claim kind
``game``) recomputes the values and re-applies the theorem's condition independently.

Novelty: results for octal games of up to three digits are tabulated (Winning Ways;
Flammenkamp's tables), and Euresis cannot search those tables from here, so each result
is labelled "novelty unchecked; may be in published tables".
"""
from __future__ import annotations

import itertools
import json
import time

import numpy as np

from .registry import ROOT, Registry

STATE = ROOT / "space" / "games_state.json"
LOG = ROOT / "space" / "games_log.md"


KNOWN_GAMES = {"77": "Kayles (Dudeney 1908; solved by Guy & Smith 1956)", "07": "Dawson's Kayles (Guy & Smith 1956)",
               "137": "Dawson's chess (Guy & Smith 1956)", "3": "Nim restricted to taking 1 (elementary)",
               "33": "subtraction game S = {1, 2} (elementary)", "333": "subtraction game S = {1, 2, 3} (elementary)"}


def grundy(code: str, N: int) -> np.ndarray:
    """Grundy values G(0..N-1) of the octal game with digits `code` (e.g. '137' for 0.137)."""
    digits = [int(ch) for ch in code]
    G = np.zeros(N, dtype=np.int64)
    for n in range(1, N):
        opts = set()
        for k, d in enumerate(digits, start=1):
            if k > n:
                break
            r = n - k
            if d & 1 and r == 0:
                opts.add(0)
            if d & 2 and r >= 1:
                opts.add(int(G[r]))
            if d & 4 and r >= 2:
                a = np.arange(1, r // 2 + 1)
                opts.update(np.bitwise_xor(G[a], G[r - a]).tolist())
        g = 0
        while g in opts:
            g += 1
        G[n] = g
    return G


def find_period(G: np.ndarray, t: int, max_p: int | None = None):
    """Smallest period p (with its pre-period n0) whose Guy–Smith condition can be certified from the
    computed values: G(n+p) = G(n) for n0 ≤ n < 2·n0 + p + t, which needs values up to 2·n0 + 2p + t."""
    N = len(G)
    max_p = max_p or N // 3
    for p in range(1, max_p + 1):
        diff = np.nonzero(G[p:] != G[:-p])[0]
        n0 = int(diff[-1]) + 1 if diff.size else 0
        if 2 * n0 + 2 * p + t <= N:
            return n0, p
    return None


def verify_claim(payload: dict) -> tuple[str, dict]:
    """Recompute G and check the Guy–Smith condition G(n+p) = G(n) for n0 ≤ n < 2·n0 + p + t."""
    code, n0, p = payload["code"], int(payload["preperiod"]), int(payload["period"])
    t = len(code)
    N = 2 * n0 + 2 * p + t + 1
    G = grundy(code, N)
    bad = [n for n in range(n0, 2 * n0 + p + t) if G[n + p] != G[n]]
    ev = {"method": "Grundy values recomputed; Guy–Smith periodicity theorem condition checked",
          "checked_up_to": N - 1, "values_of_one_period": G[n0:n0 + p].tolist()[:60]}
    if bad:
        ev["counterexample_heap"] = bad[0]
        return "refuted", ev
    return "proved", ev


def log(msg, echo=print):
    echo(msg)
    with LOG.open("a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} {msg}\n")


def codes(max_digits: int):
    for t in range(1, max_digits + 1):
        for ds in itertools.product("01234567", repeat=t):
            if ds[-1] != "0":
                yield "".join(ds)


def run(max_digits: int = 3, N: int = 1500, reg: Registry | None = None, echo=print, max_minutes: float = 60) -> dict:
    from . import gate
    reg = reg or Registry()
    st = json.loads(STATE.read_text()) if STATE.exists() else {"solved": {}, "unresolved": [], "done": []}
    t0 = time.time()
    done = set(st["done"])
    for code in codes(max_digits):
        if code in done:
            continue
        if time.time() - t0 > max_minutes * 60:
            break
        G = grundy(code, N)
        per = find_period(G, len(code))
        st["done"].append(code)
        done.add(code)
        if per is None:
            if code not in st["unresolved"]:
                st["unresolved"].append(code)
            echo(f"  0.{code}: no period found up to heap size {N} (open within this range)")
            STATE.write_text(json.dumps(st, indent=1) + "\n")
            continue
        n0, p = per
        stmt = (f"Octal game 0.{code} is completely solved: its Grundy values are periodic with pre-period {n0} "
                f"and period {p} (Guy–Smith periodicity theorem)")
        cid = reg.add("game", stmt, {"code": code, "preperiod": n0, "period": p}, source="games.py")
        if gate.check(reg, cid, log=lambda *x: None) == "proved":
            if code in KNOWN_GAMES:
                reg.set_novelty(cid, f"known ({KNOWN_GAMES[code]})")
                echo(f"  rediscovered: 0.{code} — pre-period {n0}, period {p}  ({KNOWN_GAMES[code]})")
            else:
                reg.set_novelty(cid, "novelty unchecked: octal games of up to three digits are tabulated in Winning "
                                     "Ways and Flammenkamp's tables, which cannot be searched from here")
            st["solved"][code] = {"claim": cid, "preperiod": n0, "period": p}
            if code not in KNOWN_GAMES and (p > 12 or n0 > 50):
                log(f"SOLVED (proved): 0.{code} — pre-period {n0}, period {p}  [{cid}]", echo)
        STATE.write_text(json.dumps(st, indent=1) + "\n")
    STATE.write_text(json.dumps(st, indent=1) + "\n")
    log(f"games: {len(st['solved'])} octal games solved, {len(st['unresolved'])} unresolved up to n = {N}", echo)
    return st
