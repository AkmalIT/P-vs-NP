from __future__ import annotations

from random import Random

from mcp_bench.bot import play_no_guess_game
from mcp_bench.engine import generate_board


def test_bot_deductions_are_ground_truth_correct_across_many_seeds() -> None:
    sizes = [(8, 8), (10, 10), (12, 12)]
    checked = 0
    for rows, cols in sizes:
        for seed in range(80):
            rng = Random(seed)
            first_click = (rng.randrange(rows), rng.randrange(cols))
            board = generate_board(rows, cols, first_click=first_click, rng=rng, mine_density=0.16)
            trace = play_no_guess_game(board, rng)
            for deduction in trace.deductions:
                checked += 1
                if deduction.kind == "mine":
                    assert deduction.cell in board.mine_positions
                else:
                    assert deduction.kind == "safe"
                    assert deduction.cell not in board.mine_positions
            assert board.revealed <= board.safe_cells
    assert checked > 0


def test_bot_stops_stuck_or_solved_without_guessing() -> None:
    rng = Random(123)
    first_click = (5, 5)
    board = generate_board(10, 10, first_click=first_click, rng=rng, mine_density=0.18)
    trace = play_no_guess_game(board, rng)
    assert trace.snapshots
    assert trace.stuck is (not board.is_solved)
    assert all(snapshot.revealed <= board.safe_cells for snapshot in trace.snapshots)

