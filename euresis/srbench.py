"""Law-discovery benchmark: can Euresis recover each law of its knowledge base from data alone?

For every law with a single unknown on one side, we sample its inputs (physical
constants included, as variables — the protocol of the AI Feynman benchmark,
Udrescu & Tegmark 2020) uniformly from [1, 5], compute the output, hide the
formula, and give Euresis only the numbers and the SI units of each column.

* **exact**  — the recovered symbolic equation matches the true (noiseless) law on fresh
               data to 10⁻⁶ relative error: it *is* the law, up to algebraic rearrangement —
               even when the training data carried noise;
* **approx** — matches to max(10⁻³, 3 × noise) (right behaviour, not the exact symbolic law);
* **miss**   — anything else.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np
import sympy as sp

OUT = Path(__file__).resolve().parent.parent / "space"


def _task(args):
    name, domain, expr_s, target_s, inputs, dims, target_dim, seed, noise = args
    from .dimensions import Dim
    from .engine import _Timeout, time_limit
    from .sr import regress
    rng = np.random.default_rng(seed)
    syms = [sp.Symbol(v) for v in inputs]
    truth = sp.sympify(expr_s, locals={v: s for v, s in zip(inputs, syms)})
    f = sp.lambdify(syms, truth, "numpy")

    def sample(n):
        X = rng.uniform(1, 5, (n, len(syms)))
        with np.errstate(all="ignore"):
            y = np.asarray(f(*X.T), dtype=complex) * np.ones(n)
        ok = np.isfinite(y) & (np.abs(y.imag) < 1e-12 * np.abs(y)) & (np.abs(y.real) > 1e-300)
        return X[ok], y.real[ok]
    X, y = sample(600)
    if len(y) < 100:
        return {"law": name, "domain": domain, "result": "skipped", "reason": "invalid domain"}
    X, y = X[:400], y[:400]
    if noise:
        y = y * (1 + noise * rng.standard_normal(len(y)))
    t0 = time.time()
    try:
        with time_limit(90):
            r = regress(X, y, [Dim(d) for d in dims], Dim(target_dim), inputs, seed=seed, noise=noise)
    except _Timeout:
        r = None
    except Exception as e:  # noqa: BLE001
        return {"law": name, "domain": domain, "result": "miss", "reason": f"{type(e).__name__}: {e}"[:200]}
    dt = time.time() - t0
    if r is None:
        return {"law": name, "domain": domain, "result": "miss", "seconds": round(dt, 1)}
    Xt, yt = sample(400)
    try:
        g = sp.lambdify(syms, r["expr"], "numpy")
        with np.errstate(all="ignore"):
            pred = np.asarray(g(*Xt.T), dtype=complex).real * np.ones(len(yt))
        err = float(np.max(np.abs(pred - yt) / np.abs(yt)))
    except Exception:  # noqa: BLE001
        err = float("inf")
    # exact = the symbolic law itself (agrees with the noiseless truth to 1e-6, whatever the noise);
    # approx = within max(1e-3, 3×noise) of the truth
    res = "exact" if (err < 1e-6 and r["exact"]) else ("approx" if err < max(1e-3, 3 * noise) else "miss")
    return {"law": name, "domain": domain, "result": res, "max_rel_err": err, "seconds": round(dt, 1),
            "truth": f"{target_s} = {truth}", "found": f"{target_s} = {r['expr']}", "family": r["family"],
            "pi_groups": r["pi_groups"]}


def tasks(kb, engine, noise=0.0, limit=None):
    from .engine import _as_relation
    out = []
    for i, f in enumerate(kb.formulas):
        rel = _as_relation(f)
        if not f.sym_to_q:
            continue
        lhs = f.eq.lhs
        target = lhs if isinstance(lhs, sp.Symbol) and lhs in f.sym_to_q else None
        if target is None:
            continue
        sols = engine.solve_for(rel, target)
        if not sols:
            continue
        rhs = sols[0]
        inputs = sorted(rhs.free_symbols, key=str)
        if not inputs or len(inputs) > 7:
            continue
        dims = [tuple(kb.dims[s]) for s in inputs]
        out.append((f.name, f.domain, str(rhs), f.sym_to_q[target], [str(s) for s in inputs], dims,
                    tuple(kb.dims[target]), 1000 + i, noise))
        if limit and len(out) >= limit:
            break
    return out


def run(noise=0.0, limit=None, processes=4, log=print):
    from .engine import Engine
    from .kb import KnowledgeBase
    kb = KnowledgeBase()
    eng = Engine(kb)
    ts = tasks(kb, eng, noise, limit)
    log(f"benchmark: {len(ts)} laws (noise {noise * 100:.1f}%)")
    t0 = time.time()
    with mp.Pool(processes) as pool:
        results = []
        for r in pool.imap_unordered(_task, ts, chunksize=1):
            results.append(r)
            if len(results) % 25 == 0:
                done = [x for x in results if x["result"] != "skipped"]
                ex = sum(x["result"] == "exact" for x in done)
                log(f"  {len(results)}/{len(ts)}  exact so far {ex}/{len(done)}")
    scored = [r for r in results if r["result"] != "skipped"]
    summary = {k: sum(r["result"] == k for r in scored) for k in ("exact", "approx", "miss")}
    summary.update(laws=len(scored), skipped=len(results) - len(scored), noise=noise,
                   minutes=round((time.time() - t0) / 60, 1))
    tag = "clean" if not noise else f"noise{int(noise * 1000)}"
    (OUT / f"srbench_{tag}.json").write_text(json.dumps({"summary": summary, "results": results}, indent=1))
    log(f"exact {summary['exact']}/{summary['laws']} ({100 * summary['exact'] / max(1, summary['laws']):.1f}%), "
        f"approx {summary['approx']}, miss {summary['miss']}, skipped {summary['skipped']}")
    return summary, results
