from __future__ import annotations

from mcp_bench.instance import BoardInstance, InstanceMetadata
from mcp_bench.solve import solve_instance


def test_solve_known_sat_case() -> None:
    result = solve_instance(_instance({(0, 0): 1}, [(0, 1), (1, 0), (1, 1)]), timeout_s=5)
    assert result.result == "SAT"
    assert result.solver_name == "g4"
    assert result.num_variables >= 3


def test_solve_known_unsat_case() -> None:
    result = solve_instance(
        BoardInstance(
            rows=1,
            cols=3,
            open_cells={(0, 0): 1, (0, 2): 0},
            covered_cells=[(0, 1)],
            metadata=_metadata("known-unsat", 1, 3),
        ),
        timeout_s=5,
    )
    assert result.result == "UNSAT"


def _instance(open_cells: dict[tuple[int, int], int], covered: list[tuple[int, int]]) -> BoardInstance:
    return BoardInstance(rows=2, cols=2, open_cells=open_cells, covered_cells=covered, metadata=_metadata("known-sat", 2, 2))


def _metadata(instance_id: str, rows: int, cols: int) -> InstanceMetadata:
    return InstanceMetadata(
        source="played_game",
        seed=1,
        mine_density=0.16,
        generated_at="1970-01-01T00:00:00+00:00",
        engine_git_commit="test",
        stuck_fraction_revealed=0.5,
        size=f"{rows}x{cols}",
        instance_id=instance_id,
    )

