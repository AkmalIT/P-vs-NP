"""Deterministic no-guess Minesweeper player."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from .engine import Board, Cell, neighbors, reveal, reveal_many


@dataclass(frozen=True)
class Deduction:
    kind: str
    cell: Cell
    reason: Cell


@dataclass
class BoardSnapshot:
    revealed: set[Cell]
    known_mines: set[Cell]
    fraction_revealed: float


@dataclass
class PlayTrace:
    snapshots: list[BoardSnapshot] = field(default_factory=list)
    deductions: list[Deduction] = field(default_factory=list)
    stuck: bool = False

    @property
    def final_snapshot(self) -> BoardSnapshot:
        if not self.snapshots:
            raise ValueError("play trace contains no snapshots")
        return self.snapshots[-1]


def play_no_guess_game(board: Board, rng: Random, reveal_fraction_snapshots: float | None = None) -> PlayTrace:
    """Play using only single-point deterministic deductions.

    The bot keeps an internal set of known mines, then performs a fixed-point
    pass over revealed numbered frontier cells. It never opens an unrevealed
    cell unless the local clue equation proves that every remaining neighbor is
    safe, and it never marks a mine unless the local clue equation proves that
    every remaining neighbor is mined.
    """
    if not board.revealed:
        first_click = board.first_click if board.first_click is not None else _choose_safe_first_click(board, rng)
        reveal(board, first_click)

    known_mines: set[Cell] = set()
    trace = PlayTrace()
    _append_snapshot(trace, board, known_mines)
    target_fraction = reveal_fraction_snapshots
    target_recorded = False

    while not board.is_solved:
        made_progress = False
        forced_mines: set[Cell] = set()
        forced_safe: set[Cell] = set()

        for clue_cell in sorted(board.revealed):
            clue = board.numbers[clue_cell]
            ns = set(neighbors(board.rows, board.cols, clue_cell))
            hidden_neighbors = ns - board.revealed - known_mines
            known_adjacent_mines = len(ns & known_mines)

            if hidden_neighbors and clue - known_adjacent_mines == len(hidden_neighbors):
                for cell in sorted(hidden_neighbors):
                    if cell not in known_mines:
                        forced_mines.add(cell)
                        trace.deductions.append(Deduction("mine", cell, clue_cell))

            if hidden_neighbors and clue == known_adjacent_mines:
                for cell in sorted(hidden_neighbors):
                    forced_safe.add(cell)
                    trace.deductions.append(Deduction("safe", cell, clue_cell))

        if forced_mines - known_mines:
            known_mines.update(forced_mines)
            made_progress = True
        forced_safe -= board.revealed
        forced_safe -= known_mines
        if forced_safe:
            reveal_many(board, sorted(forced_safe))
            made_progress = True

        if made_progress:
            _append_snapshot(trace, board, known_mines)
            if target_fraction is not None and not target_recorded and _fraction_revealed(board) >= target_fraction:
                target_recorded = True
        else:
            trace.stuck = True
            break

    if board.is_solved:
        trace.stuck = False
        if trace.snapshots[-1].revealed != board.revealed:
            _append_snapshot(trace, board, known_mines)
    return trace


def first_snapshot_at_fraction(trace: PlayTrace, fallback_reveal_fraction: float) -> BoardSnapshot:
    for snapshot in trace.snapshots:
        if snapshot.fraction_revealed >= fallback_reveal_fraction:
            return snapshot
    return trace.final_snapshot


def _choose_safe_first_click(board: Board, rng: Random) -> Cell:
    safe = sorted(board.safe_cells)
    if not safe:
        raise ValueError("board has no safe cells to reveal")
    return safe[rng.randrange(len(safe))]


def _append_snapshot(trace: PlayTrace, board: Board, known_mines: set[Cell]) -> None:
    trace.snapshots.append(
        BoardSnapshot(
            revealed=set(board.revealed),
            known_mines=set(known_mines),
            fraction_revealed=_fraction_revealed(board),
        )
    )


def _fraction_revealed(board: Board) -> float:
    return len(board.revealed) / (board.rows * board.cols)

