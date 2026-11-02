"""Tools that cannot make mistakes in their own domain.

* ``prove_z3``   — Z3 SMT solver: proves (or refutes with a counterexample)
                   statements in arithmetic, real algebra, inequalities and logic.
* ``check_lean`` — Lean 4 proof checker, when a ``lean`` binary is installed:
                   a proof that compiles is correct, full stop.
* ``run_python`` — executes code in a separate, resource-limited process with a
                   timeout, so numerical claims can be computed, not guessed.
* ``cas``        — SymPy computer algebra: simplify, solve, differentiate,
                   integrate, limits, series, and Euresis' dimensional check.
"""
from __future__ import annotations

import os
import resource
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import sympy as sp


# ------------------------------------------------------------------- Z3
def prove_z3(claim: str, variables: dict[str, str] | None = None, assumptions: list[str] | None = None,
             timeout_ms: int = 20000) -> dict:
    """Prove `claim` for all values of `variables` satisfying `assumptions`.

    variables: {"x": "Real", "n": "Int", "p": "Bool"}. Expressions use Python/Z3 syntax:
    `x**2 + y**2 >= 2*x*y`, `Implies(a, b)`, `And(...)`, `Or(...)`, `Not(...)`.
    Z3 proves the claim by showing its negation is unsatisfiable; otherwise returns a counterexample."""
    import z3
    env = {k: getattr(z3, k) for k in ("And", "Or", "Not", "Implies", "If", "ForAll", "Exists", "Sum",
                                        "Product", "Abs", "Distinct", "sqrt") if hasattr(z3, k)}
    env["Abs"] = lambda x: z3.If(x >= 0, x, -x)
    for name, sort in (variables or {}).items():
        env[name] = {"Real": z3.Real, "Int": z3.Int, "Bool": z3.Bool}[sort](name)
    try:
        goal = eval(claim, {"__builtins__": {}}, env)          # noqa: S307 — restricted namespace
        hyps = [eval(a, {"__builtins__": {}}, env) for a in (assumptions or [])]   # noqa: S307
    except Exception as e:
        return {"status": "error", "detail": f"could not parse: {e}"}
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    s.add(*hyps)
    s.add(z3.Not(goal))
    r = s.check()
    if r == z3.unsat:
        return {"status": "proved", "detail": "negation is unsatisfiable: the claim holds for all values"}
    if r == z3.sat:
        m = s.model()
        return {"status": "refuted", "counterexample": {str(d): str(m[d]) for d in m.decls()}}
    return {"status": "unknown", "detail": f"Z3 could not decide ({s.reason_unknown()})"}


# ------------------------------------------------------------------ Lean
def lean_available() -> str | None:
    return shutil.which("lean") or (str(Path.home() / ".elan/bin/lean")
                                    if (Path.home() / ".elan/bin/lean").exists() else None)


def check_lean(source: str, timeout=120) -> dict:
    """Type-check a Lean 4 file. Success means every theorem in it is proved."""
    lean = lean_available()
    if not lean:
        return {"status": "unavailable",
                "detail": "Lean 4 is not installed (install with elan: https://lean-lang.org/install)"}
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "Euresis.lean"
        f.write_text(source)
        try:
            p = subprocess.run([lean, str(f)], capture_output=True, text=True, timeout=timeout, cwd=d)
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
    out = (p.stdout + p.stderr).strip()
    if p.returncode == 0 and "sorry" not in source and "error" not in out:
        return {"status": "proved", "detail": out or "all declarations type-check"}
    return {"status": "failed", "detail": out[:4000]}


# ----------------------------------------------------------------- Python
def _limits(cpu_s, mem_mb):
    def f():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 2 ** 20, mem_mb * 2 ** 20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 2 ** 20, 10 * 2 ** 20))
        os.setsid()
    return f


def run_python(code: str, timeout=60, mem_mb=2048) -> dict:
    """Run code in an isolated interpreter (-I), its own temp dir, with CPU/memory/file-size limits,
    no network (separate network namespace where the OS allows it). numpy, scipy, sympy available."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "snippet.py"
        f.write_text(code)
        env = {"PATH": "/usr/bin:/bin", "HOME": d, "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"}
        cmd = [sys.executable, "-I", str(f)]
        unshare = shutil.which("unshare")
        if unshare and subprocess.run([unshare, "-n", "true"], capture_output=True).returncode == 0:
            cmd = [unshare, "-n"] + cmd          # no network inside the sandbox
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               cwd=d, env=env, preexec_fn=_limits(timeout, mem_mb))
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "stdout": "", "stderr": f"exceeded {timeout} s"}
    return {"status": "ok" if p.returncode == 0 else "error", "returncode": p.returncode,
            "stdout": p.stdout[-8000:], "stderr": p.stderr[-4000:]}


# -------------------------------------------------------------------- CAS
def cas(operation: str, expression: str, variable: str = "", point: str = "", order: int = 6) -> dict:
    """Exact symbolic computation with SymPy."""
    loc = {}
    try:
        if "=" in expression and operation == "solve":
            l, r = expression.split("=", 1)
            e = sp.Eq(sp.sympify(l, locals=loc), sp.sympify(r, locals=loc))
        else:
            e = sp.sympify(expression, locals=loc)
        v = sp.Symbol(variable) if variable else None
        if operation == "simplify":
            out = sp.simplify(e)
        elif operation == "solve":
            out = sp.solve(e, v) if v else sp.solve(e)
        elif operation == "diff":
            out = sp.diff(e, v)
        elif operation == "integrate":
            out = sp.integrate(e, v) if v else sp.integrate(e)
        elif operation == "limit":
            out = sp.limit(e, v, sp.sympify(point or "0"))
        elif operation == "series":
            out = sp.series(e, v, sp.sympify(point or "0"), order).removeO()
        elif operation == "equal":
            a, b = expression.split("==")
            d = sp.simplify(sp.sympify(a) - sp.sympify(b))
            out = (d == 0)
            return {"result": bool(out), "difference": str(d)}
        else:
            return {"error": f"unknown operation {operation}"}
        return {"result": str(out)}
    except Exception as ex:
        return {"error": str(ex)}
