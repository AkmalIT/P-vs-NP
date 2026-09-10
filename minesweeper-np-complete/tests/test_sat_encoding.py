from __future__ import annotations

from pysat.solvers import Solver

from mcp_bench.instance import BoardInstance, InstanceMetadata
from mcp_bench.sat_encoding import encode_instance


def test_encoding_sat_case() -> None:
    instance = _instance(2, 2, {(0, 0): 1}, [(0, 1), (1, 0), (1, 1)])
    assert _is_sat(instance)


def test_encoding_unsat_contradictory_clues() -> None:
    instance = _instance(1, 3, {(0, 0): 1, (0, 2): 0}, [(0, 1)])
    assert not _is_sat(instance)


def test_encoding_fully_clued_unique_solution() -> None:
    instance = _instance(2, 2, {(0, 1): 1, (1, 0): 1, (1, 1): 1}, [(0, 0)])
    cnf = encode_instance(instance)
    with Solver(name="g4", bootstrap_with=cnf.clauses) as solver:
        assert solver.solve()
        model = set(solver.get_model())
    assert 1 in model
    with Solver(name="g4", bootstrap_with=cnf.clauses + [[-1]]) as solver:
        assert not solver.solve()


def _is_sat(instance: BoardInstance) -> bool:
    cnf = encode_instance(instance)
    with Solver(name="g4", bootstrap_with=cnf.clauses) as solver:
        return bool(solver.solve())


def _instance(rows: int, cols: int, open_cells: dict[tuple[int, int], int], covered: list[tuple[int, int]]) -> BoardInstance:
    return BoardInstance(
        rows=rows,
        cols=cols,
        open_cells=open_cells,
        covered_cells=covered,
        metadata=InstanceMetadata(
            source="played_game",
            seed=1,
            mine_density=0.16,
            generated_at="1970-01-01T00:00:00+00:00",
            engine_git_commit="test",
            stuck_fraction_revealed=len(open_cells) / (rows * cols),
            size=f"{rows}x{cols}",
            instance_id="test",
        ),
    )

