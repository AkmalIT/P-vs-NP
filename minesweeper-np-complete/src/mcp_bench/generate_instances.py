"""CLI for generating played-game and uniform-random MCP instances."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from typing import Sequence

from .bot import first_snapshot_at_fraction, play_no_guess_game
from .engine import Cell, generate_board, generate_uniform_random_board, mine_count_from_density
from .instance import BoardInstance, InstanceMetadata, instance_from_revealed


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    generated_at = args.generated_at or datetime.now(UTC).isoformat()
    git_commit = _git_commit()

    written_files: list[Path] = []
    for size in args.sizes:
        path = out / f"{size}x{size}.jsonl"
        instances: list[BoardInstance] = []
        for game_idx in range(args.games_per_size):
            played_seed = _derive_seed(args.seed, size, game_idx, "played_game")
            uniform_seed = _derive_seed(args.seed, size, game_idx, "uniform_random")
            instances.append(
                generate_played_game_instance(
                    rows=size,
                    cols=size,
                    seed=played_seed,
                    source_index=game_idx,
                    mine_density=args.mine_density,
                    mine_count=args.mine_count,
                    fallback_reveal_fraction=args.fallback_reveal_fraction,
                    generated_at=generated_at,
                    git_commit=git_commit,
                )
            )
            instances.append(
                generate_uniform_random_instance(
                    rows=size,
                    cols=size,
                    seed=uniform_seed,
                    source_index=game_idx,
                    mine_density=args.mine_density,
                    mine_count=args.mine_count,
                    reveal_fraction=args.fallback_reveal_fraction,
                    generated_at=generated_at,
                    git_commit=git_commit,
                )
            )
        path.write_text("".join(instance.to_json() + "\n" for instance in instances), encoding="utf-8")
        written_files.append(path)

    manifest = {
        "generated_at": generated_at,
        "cli_args": vars(args),
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_commit": git_commit,
        "package_versions": _pip_freeze(),
        "files": {
            path.name: {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "instances": sum(1 for _ in path.open("r", encoding="utf-8")),
            }
            for path in sorted(written_files)
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate_played_game_instance(
    rows: int,
    cols: int,
    seed: int,
    source_index: int,
    mine_density: float = 0.16,
    mine_count: int | None = None,
    fallback_reveal_fraction: float = 0.4,
    generated_at: str = "1970-01-01T00:00:00+00:00",
    git_commit: str = "unknown",
) -> BoardInstance:
    rng = Random(seed)
    first_click = (rng.randrange(rows), rng.randrange(cols))
    count = mine_count if mine_count is not None else mine_count_from_density(rows, cols, mine_density)
    board = generate_board(rows, cols, count, first_click, rng, mine_density)
    trace = play_no_guess_game(board, rng)
    snapshot = trace.final_snapshot if trace.stuck else first_snapshot_at_fraction(trace, fallback_reveal_fraction)
    metadata = InstanceMetadata(
        source="played_game",
        seed=seed,
        mine_density=mine_density,
        generated_at=generated_at,
        engine_git_commit=git_commit,
        stuck_fraction_revealed=snapshot.fraction_revealed,
        size=f"{rows}x{cols}",
        instance_id=f"played_game-{rows}x{cols}-{source_index:05d}-{seed}",
    )
    return instance_from_revealed(board, snapshot.revealed, metadata)


def generate_uniform_random_instance(
    rows: int,
    cols: int,
    seed: int,
    source_index: int,
    mine_density: float = 0.16,
    mine_count: int | None = None,
    reveal_fraction: float = 0.4,
    generated_at: str = "1970-01-01T00:00:00+00:00",
    git_commit: str = "unknown",
) -> BoardInstance:
    rng = Random(seed)
    count = mine_count if mine_count is not None else mine_count_from_density(rows, cols, mine_density)
    board = generate_uniform_random_board(rows, cols, count, rng, mine_density)
    safe_cells = sorted(board.safe_cells)
    target = min(len(safe_cells), max(1, round(rows * cols * reveal_fraction)))
    revealed: set[Cell] = set(rng.sample(safe_cells, target))
    metadata = InstanceMetadata(
        source="uniform_random",
        seed=seed,
        mine_density=mine_density,
        generated_at=generated_at,
        engine_git_commit=git_commit,
        stuck_fraction_revealed=len(revealed) / (rows * cols),
        size=f"{rows}x{cols}",
        instance_id=f"uniform_random-{rows}x{cols}-{source_index:05d}-{seed}",
    )
    return instance_from_revealed(board, revealed, metadata)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", required=True, type=lambda value: [int(v) for v in value.split(",")])
    parser.add_argument("--games-per-size", required=True, type=int)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mine-density", type=float, default=0.16)
    parser.add_argument("--mine-count", type=int, default=None)
    parser.add_argument("--fallback-reveal-fraction", type=float, default=0.4)
    parser.add_argument("--generated-at", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def _derive_seed(base_seed: int, size: int, index: int, source: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{size}:{index}:{source}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _pip_freeze() -> list[str]:
    try:
        output = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return sorted(line for line in output.splitlines() if line)


if __name__ == "__main__":
    main()

