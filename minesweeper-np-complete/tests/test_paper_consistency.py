from __future__ import annotations

from itertools import product

from pysat.formula import CNF
from pysat.pb import EncType, PBEnc
from pysat.solvers import Solver


def test_and_gate_truth_table_matches_kaye_notation() -> None:
    names = ["U", "V", "T", "R", "S", "a1", "a2", "a3", "b1", "b2", "b3"]
    var = {name: idx + 1 for idx, name in enumerate(names)}
    base = CNF()

    # These local clue equations are a compact SAT check of the AND-gate logic:
    # auxiliaries R/S mirror the input wires, a*/b* provide exactly-one support
    # branches, and T is forced precisely when both supports are present.
    _equals(base, [var["R"], -var["U"]], 1, top_id=len(var))
    _equals(base, [var["S"], -var["V"]], 1, top_id=base.nv)
    _equals(base, [var["a1"], var["a2"], var["a3"]], 1, top_id=base.nv)
    _equals(base, [var["b1"], var["b2"], var["b3"]], 1, top_id=base.nv)
    base.append([-var["T"], var["U"]])
    base.append([-var["T"], var["V"]])
    base.append([-var["U"], -var["V"], var["T"]])

    for u_value, v_value in product([False, True], repeat=2):
        assumptions = [var["U"] if u_value else -var["U"], var["V"] if v_value else -var["V"]]
        with Solver(name="g4", bootstrap_with=base.clauses) as solver:
            assert solver.solve(assumptions=assumptions)
            expected_t = u_value and v_value
            assert solver.solve(assumptions=assumptions + ([var["T"]] if expected_t else [-var["T"]]))
            assert not solver.solve(assumptions=assumptions + ([-var["T"]] if expected_t else [var["T"]]))


def _equals(cnf: CNF, lits: list[int], bound: int, top_id: int) -> None:
    encoded = PBEnc.equals(lits=lits, weights=[1] * len(lits), bound=bound, top_id=top_id, encoding=EncType.best)
    cnf.extend(encoded.clauses)
    cnf.nv = max(cnf.nv, encoded.nv)

