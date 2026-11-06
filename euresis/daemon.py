"""Always-on discovery: one process that keeps every Euresis engine running, online or offline.

    python -m euresis daemon                      # run forever
    python -m euresis daemon --hours 1.75         # one time-boxed run (for schedulers / cloud sessions)
    python -m euresis daemon --git-push           # commit and push results after every slice

Each cycle runs, in turn, for a time slice:
  1. data feeds        — published datasets from Zenodo / Figshare when online; datasets on disk when offline
  2. physics + economics — two-variable proved bounds (uses the local 14B model if installed)
  3. music + games     — proofs by exhaustion across tunings; octal games by the Guy–Smith theorem
Everything is saved after each slice, so the daemon can be stopped and restarted at any time
(create data/STOP to stop it after the current slice).

To keep it running on your own computer:
  Linux/macOS:  nohup python -m euresis daemon --git-push > euresis.log 2>&1 &
  or a cron entry / systemd service that runs `python -m euresis daemon --hours 1` every hour.
"""
from __future__ import annotations

import subprocess
import time

from .registry import ROOT

STOP = ROOT / "data" / "STOP"


def _git_push(log):
    def run(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    for _ in range(3):
        if run("add", "-A").returncode == 0:
            break
        (ROOT / ".git" / "index.lock").unlink(missing_ok=True)
        time.sleep(2)
    if run("diff", "--cached", "--quiet").returncode == 0:
        return
    run("commit", "-q", "-m", "Euresis daemon: discovery progress")
    for i in range(4):
        # another shift may have pushed meanwhile: replay our commit on top (state files: keep ours)
        run("pull", "-q", "--rebase", "-X", "theirs")
        if run("push", "-q").returncode == 0:
            log("  results committed and pushed")
            return
        time.sleep(2 ** (i + 1))
    log("  push failed (offline?) — results are committed locally")


def run(hours: float | None = None, slice_minutes: float = 30, git_push: bool = False, log=print):
    from . import datafeeds, local_llm, physics_discover2, subjects
    t_end = time.time() + hours * 3600 if hours else None
    cycle = 0
    log(f"Euresis daemon started ({'forever' if not hours else f'{hours} h'}; slices of {slice_minutes:.0f} min; "
        f"local model {'available' if local_llm.available() else 'not installed'})")
    while True:
        cycle += 1
        for name, step in (("data feeds", lambda m: datafeeds.run(minutes=m)),
                           ("physics + economics", lambda m: physics_discover2.run(minutes=m)),
                           ("music + games", lambda m: subjects.run_segment(minutes=m))):
            if STOP.exists():
                log("STOP file found — daemon stopping")
                return
            left = (t_end - time.time()) / 60 if t_end else slice_minutes
            if left < 1:
                log("time budget used — daemon stopping")
                return
            m = min(slice_minutes, left)
            log(f"== cycle {cycle}: {name} ({m:.0f} min, {'online' if datafeeds.online() else 'offline'})")
            try:
                step(m)
            except Exception as e:                       # one engine failing must not stop discovery
                log(f"  {name} failed: {type(e).__name__}: {e}")
            try:                                         # keep the published chat's results current
                from .chat import export_site
                export_site(log=log)
            except Exception as e:
                log(f"  website update failed: {type(e).__name__}: {e}")
            if git_push:
                _git_push(log)
