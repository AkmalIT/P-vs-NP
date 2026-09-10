from __future__ import annotations

from random import Random

import pytest

from mcp_bench.engine import Board, generate_board, neighbors, reveal


def test_neighbors_are_8_connected_and_edge_clipped() -> None:
    assert neighbors(3, 3, (0, 0)) == [(0, 1), (1, 0), (1, 1)]
    assert set(neighbors(3, 3, (1, 1))) == {
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 2),
        (2, 0),
        (2, 1),
        (2, 2),
    }


def test_generate_board_respects_mine_count_and_safe_first_click() -> None:
    rng = Random(7)
    first = (2, 2)
    board = generate_board(8, 8, mine_count=12, first_click=first, rng=rng)
    protected = set(neighbors(8, 8, first)) | {first}
    assert len(board.mine_positions) == 12
    assert not (board.mine_positions & protected)


def test_generate_board_rejects_too_many_mines() -> None:
    with pytest.raises(ValueError, match="too large"):
        generate_board(3, 3, mine_count=1, first_click=(1, 1), rng=Random(1))


def test_reveal_flood_fill_single_corner_mine_reveals_all_safe_cells() -> None:
    board = Board(rows=3, cols=3, mine_positions={(0, 0)})
    newly = reveal(board, (2, 2))
    assert newly == {
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, 0),
        (2, 1),
        (2, 2),
    }


def test_reveal_numbered_cell_does_not_flood_fill() -> None:
    board = Board(rows=4, cols=4, mine_positions={(2, 2)})
    newly = reveal(board, (3, 3))
    assert newly == {(3, 3)}
    assert board.revealed == {(3, 3)}

