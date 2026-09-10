"""SAT solving wrapper and benchmark metadata."""

from __future__ import annotations

import multiprocessing as mp
import os
import time
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from pysat.formula import CNF
from pysat.solvers import Solver

from .instance import BoardInstance
from .sat_encoding import encode_instance

SolveStatus = Literal["SAT", "UNSAT", "TIMEOUT"]


@dataclass(frozen=True)
class SolveResult:
    solve_time_s: float
    encode_time_s: float
    result: SolveStatus
    num_variables: int
    num_clauses: int
    solver_name: str
    solver_version: str

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def solve_instance(instance: BoardInstance, timeout_s: float | None = None) -> SolveResult:
    """Encode and solve an MCP instance with Glucose4.

    Time spent in ``encode_instance`` is measured separately from the SAT call.
    Timeouts use ``multiprocessing`` so the approach works on Linux, macOS, and
    Windows; the measured solve time includes solver construction in the child
    process but excludes CNF encoding in the parent process.
    """
    solver_name = "g4"
    solver_version = _solver_version()
    encode_start = time.perf_counter()
    cnf = encode_instance(instance)
    encode_time_s = time.perf_counter() - encode_start

    if timeout_s is not None:
        solve_time_s, status = _solve_with_process_timeout(cnf, solver_name, timeout_s)
    else:
        solve_start = time.perf_counter()
        sat = _solve_cnf(cnf, solver_name)
        solve_time_s = time.perf_counter() - solve_start
        status = "SAT" if sat else "UNSAT"

    return SolveResult(
        solve_time_s=solve_time_s,
        encode_time_s=encode_time_s,
        result=status,
        num_variables=cnf.nv,
        num_clauses=len(cnf.clauses),
        solver_name=solver_name,
        solver_version=solver_version,
    )


def _solve_cnf(cnf: CNF, solver_name: str) -> bool:
    with Solver(name=solver_name, bootstrap_with=cnf.clauses) as solver:
        return bool(solver.solve())


def _solve_worker(cnf: CNF, solver_name: str, queue: mp.Queue[bool]) -> None:
    queue.put(_solve_cnf(cnf, solver_name))


def _solve_with_process_timeout(cnf: CNF, solver_name: str, timeout_s: float) -> tuple[float, SolveStatus]:
    context = mp.get_context("fork") if os.name == "posix" else mp.get_context()
    queue: mp.Queue[bool] = context.Queue(maxsize=1)
    process = context.Process(target=_solve_worker, args=(cnf, solver_name, queue))
    solve_start = time.perf_counter()
    process.start()
    process.join(timeout_s)
    solve_time_s = time.perf_counter() - solve_start
    if process.is_alive():
        process.terminate()
        process.join()
        return solve_time_s, "TIMEOUT"
    if process.exitcode != 0:
        raise RuntimeError(f"solver subprocess exited with status {process.exitcode}")
    sat = queue.get_nowait()
    return solve_time_s, "SAT" if sat else "UNSAT"


def _solver_version() -> str:
    try:
        return version("python-sat")
    except PackageNotFoundError:
        return "unknown"
