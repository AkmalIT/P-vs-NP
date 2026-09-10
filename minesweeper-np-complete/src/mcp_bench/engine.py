"""Minesweeper board generation and reveal mechanics.

The default generator uses the common "safe first click" convention: mines are
sampled uniformly from all cells except the first clicked cell and its eight
neighbors. This mirrors mainstream Minesweeper implementations, where the
opening click should not immediately lose and should expose a playable local
region rather than an isolated number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Iterable

Cell = tuple[int, int]


@dataclass
class Board:
    rows: int
    cols: int
    mine_positions: set[Cell]
    revealed: set[Cell] = field(default_factory=set)
    numbers: dict[Cell, int] = field(default_factory=dict)
    first_click: Cell | None = None

    def __post_init__(self) -> None:
        for cell in self.mine_positions:
            _validate_cell(self.rows, self.cols, cell)
        if not self.numbers:
            self.numbers = {
                (r, c): count_adjacent_mines(self.mine_positions, self.rows, self.cols, (r, c))
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) not in self.mine_positions
            }

    @property
    def safe_cells(self) -> set[Cell]:
        return {
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in self.mine_positions
        }

    @property
    def is_solved(self) -> bool:
        return self.safe_cells <= self.revealed

    def copy_with_revealed(self, revealed: set[Cell]) -> "Board":
        return Board(
            rows=self.rows,
            cols=self.cols,
            mine_positions=set(self.mine_positions),
            revealed=set(revealed),
            numbers=dict(self.numbers),
            first_click=self.first_click,
        )


def neighbors(rows: int, cols: int, cell: Cell) -> list[Cell]:
    """Return 8-connected neighbors clipped to the board."""
    r, c = cell
    _validate_cell(rows, cols, cell)
    return [
        (rr, cc)
        for rr in range(max(0, r - 1), min(rows, r + 2))
        for cc in range(max(0, c - 1), min(cols, c + 2))
        if (rr, cc) != cell
    ]


def count_adjacent_mines(mine_positions: set[Cell], rows: int, cols: int, cell: Cell) -> int:
    return sum(n in mine_positions for n in neighbors(rows, cols, cell))


def mine_count_from_density(rows: int, cols: int, mine_density: float = 0.16) -> int:
    if not 0 <= mine_density < 1:
        raise ValueError(f"mine_density must be in [0, 1), got {mine_density}")
    return round(rows * cols * mine_density)


def generate_board(
    rows: int,
    cols: int,
    mine_count: int | None = None,
    first_click: Cell | None = None,
    rng: Random | None = None,
    mine_density: float = 0.16,
) -> Board:
    """Generate a board with uniformly sampled mines and a safe first click."""
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive")
    rng = rng or Random()
    first_click = first_click if first_click is not None else (rng.randrange(rows), rng.randrange(cols))
    _validate_cell(rows, cols, first_click)
    mine_count = mine_count_from_density(rows, cols, mine_density) if mine_count is None else mine_count

    excluded = set(neighbors(rows, cols, first_click)) | {first_click}
    candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in excluded]
    if mine_count > len(candidates):
        raise ValueError(
            f"mine_count={mine_count} is too large for a {rows}x{cols} board "
            f"with safe first click at {first_click}; maximum is {len(candidates)}"
        )
    if mine_count < 0:
        raise ValueError("mine_count must be non-negative")
    mine_positions = set(rng.sample(candidates, mine_count))
    return Board(rows=rows, cols=cols, mine_positions=mine_positions, first_click=first_click)


def generate_uniform_random_board(
    rows: int,
    cols: int,
    mine_count: int | None = None,
    rng: Random | None = None,
    mine_density: float = 0.16,
) -> Board:
    """Generate a board by sampling mines uniformly from all cells."""
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive")
    rng = rng or Random()
    mine_count = mine_count_from_density(rows, cols, mine_density) if mine_count is None else mine_count
    all_cells = [(r, c) for r in range(rows) for c in range(cols)]
    if not 0 <= mine_count <= len(all_cells):
        raise ValueError(f"mine_count must be between 0 and {len(all_cells)}, got {mine_count}")
    return Board(rows=rows, cols=cols, mine_positions=set(rng.sample(all_cells, mine_count)))


def reveal(board: Board, cell: Cell) -> set[Cell]:
    """Reveal a cell, flood-filling through connected zero cells."""
    _validate_cell(board.rows, board.cols, cell)
    if cell in board.mine_positions:
        raise ValueError(f"cannot reveal mined cell {cell}")
    if cell in board.revealed:
        return set()

    newly_revealed: set[Cell] = set()
    stack = [cell]
    while stack:
        current = stack.pop()
        if current in board.revealed or current in newly_revealed or current in board.mine_positions:
            continue
        newly_revealed.add(current)
        if board.numbers[current] == 0:
            stack.extend(
                n
                for n in neighbors(board.rows, board.cols, current)
                if n not in board.revealed and n not in newly_revealed and n not in board.mine_positions
            )
    board.revealed.update(newly_revealed)
    return newly_revealed


def reveal_many(board: Board, cells: Iterable[Cell]) -> set[Cell]:
    newly: set[Cell] = set()
    for cell in sorted(cells):
        newly.update(reveal(board, cell))
    return newly


def _validate_cell(rows: int, cols: int, cell: Cell) -> None:
    r, c = cell
    if not (0 <= r < rows and 0 <= c < cols):
        raise ValueError(f"cell {cell} is outside a {rows}x{cols} board")

