"""SAT/PB encoding for the Minesweeper Consistency Problem."""

from __future__ import annotations

from pysat.formula import CNF
from pysat.pb import EncType, PBEnc

from .engine import Cell, neighbors
from .instance import BoardInstance


def encode_instance(instance: BoardInstance) -> CNF:
    """Encode an instance as CNF using one Boolean variable per covered cell.

    The implementation intentionally mirrors the paper listing: ``var_map``
    maps covered cells to SAT variables, ``neighbors`` are the covered neighbors
    of an open clue, and ``target`` is the clue value to satisfy.
    """
    var_map: dict[Cell, int] = {cell: idx + 1 for idx, cell in enumerate(sorted(instance.covered_cells))}
    cnf = CNF()
    cnf.nv = len(var_map)

    for clue_cell, clue in sorted(instance.open_cells.items()):
        neighbors_lits = [
            var_map[cell]
            for cell in neighbors(instance.rows, instance.cols, clue_cell)
            if cell in var_map
        ]
        target = clue
        if target < 0 or target > len(neighbors_lits):
            cnf.append([])
            continue
        if not neighbors_lits:
            if target != 0:
                cnf.append([])
            continue
        encoded = PBEnc.equals(
            lits=neighbors_lits,
            weights=[1] * len(neighbors_lits),
            bound=target,
            top_id=cnf.nv,
            encoding=EncType.best,
        )
        cnf.extend(encoded.clauses)
        cnf.nv = max(cnf.nv, encoded.nv)
    return cnf

