"""Serializable Minesweeper consistency instances."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .engine import Board, Cell

Source = Literal["played_game", "uniform_random"]


@dataclass(frozen=True)
class InstanceMetadata:
    source: Source
    seed: int
    mine_density: float
    generated_at: str
    engine_git_commit: str
    stuck_fraction_revealed: float
    size: str
    instance_id: str


@dataclass(frozen=True)
class BoardInstance:
    rows: int
    cols: int
    open_cells: dict[Cell, int]
    covered_cells: list[Cell]
    metadata: InstanceMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "open_cells": {cell_to_key(cell): self.open_cells[cell] for cell in sorted(self.open_cells)},
            "covered_cells": [list(cell) for cell in sorted(self.covered_cells)],
            "metadata": {
                "source": self.metadata.source,
                "seed": self.metadata.seed,
                "mine_density": self.metadata.mine_density,
                "generated_at": self.metadata.generated_at,
                "engine_git_commit": self.metadata.engine_git_commit,
                "stuck_fraction_revealed": self.metadata.stuck_fraction_revealed,
                "size": self.metadata.size,
                "instance_id": self.metadata.instance_id,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardInstance":
        metadata = InstanceMetadata(
            source=data["metadata"]["source"],
            seed=int(data["metadata"]["seed"]),
            mine_density=float(data["metadata"]["mine_density"]),
            generated_at=str(data["metadata"]["generated_at"]),
            engine_git_commit=str(data["metadata"]["engine_git_commit"]),
            stuck_fraction_revealed=float(data["metadata"]["stuck_fraction_revealed"]),
            size=str(data["metadata"]["size"]),
            instance_id=str(data["metadata"]["instance_id"]),
        )
        return cls(
            rows=int(data["rows"]),
            cols=int(data["cols"]),
            open_cells={key_to_cell(key): int(value) for key, value in data["open_cells"].items()},
            covered_cells=[(int(cell[0]), int(cell[1])) for cell in data["covered_cells"]],
            metadata=metadata,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, line: str) -> "BoardInstance":
        return cls.from_dict(json.loads(line))


def instance_from_revealed(
    board: Board,
    revealed: set[Cell],
    metadata: InstanceMetadata,
) -> BoardInstance:
    open_cells = {cell: board.numbers[cell] for cell in sorted(revealed)}
    covered_cells = [
        (r, c)
        for r in range(board.rows)
        for c in range(board.cols)
        if (r, c) not in revealed
    ]
    return BoardInstance(
        rows=board.rows,
        cols=board.cols,
        open_cells=open_cells,
        covered_cells=covered_cells,
        metadata=metadata,
    )


def cell_to_key(cell: Cell) -> str:
    return f"{cell[0]},{cell[1]}"


def key_to_cell(key: str) -> Cell:
    r, c = key.split(",", maxsplit=1)
    return int(r), int(c)

