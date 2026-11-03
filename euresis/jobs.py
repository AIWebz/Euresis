"""Job queue for long-running work (e.g. rigorous orbit proofs that take hours).

Jobs live in the registry database, so they survive restarts: a worker that dies
leaves its job 'running', and ``requeue_stale`` puts it back in the queue.

    python -m euresis jobs list
    python -m euresis jobs work            # process until the queue is empty
    python -m euresis jobs work --forever  # keep polling (run under nohup/systemd)
"""
from __future__ import annotations

import time
import traceback

from . import gate
from .registry import Registry


def _run_gate(reg: Registry, args: dict, log):
    return {"status": gate.check(reg, args["claim"], log=log)}


HANDLERS = {"gate": _run_gate}


def work(reg: Registry | None = None, forever=False, poll_s=30, max_jobs: int | None = None, log=print) -> int:
    reg = reg or Registry()
    reg.requeue_stale()
    done = 0
    while max_jobs is None or done < max_jobs:
        job = reg.claim_job()
        if job is None:
            if not forever:
                break
            time.sleep(poll_s)
            continue
        log(f"job {job['id']} ({job['kind']}) {job['args']}")
        handler = HANDLERS.get(job["kind"])
        try:
            if handler is None:
                raise ValueError(f"no handler for job kind {job['kind']!r}")
            reg.finish_job(job["id"], result=handler(reg, job["args"], log))
        except Exception as e:
            reg.finish_job(job["id"], error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[-2000:]}")
            log(f"  job {job['id']} failed: {e}")
        done += 1
    return done
