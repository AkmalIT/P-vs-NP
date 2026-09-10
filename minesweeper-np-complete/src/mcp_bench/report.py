"""Aggregate benchmark output into a table and plot."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

import matplotlib.pyplot as plt


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    run_dir = Path(args.run)
    rows = _read_raw(run_dir / "raw.jsonl")
    summary = _summarize_for_report(rows)
    markdown = _markdown_table(summary)
    (run_dir / "summary.md").write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    _plot(summary, run_dir / "plot.png")


def _read_raw(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _summarize_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, str], list[float]] = defaultdict(list)
    timeouts: dict[tuple[int, str], int] = defaultdict(int)
    for row in rows:
        size = int(row["metadata"]["size"].split("x")[0])
        source = row["metadata"]["source"]
        key = (size, source)
        if row["solve"]["result"] == "TIMEOUT":
            timeouts[key] += 1
        else:
            groups[key].append(float(row["solve"]["solve_time_s"]))
    summary: list[dict[str, Any]] = []
    for key in sorted(set(groups) | set(timeouts)):
        times = groups[key]
        mean = sum(times) / len(times) if times else None
        summary.append({"size": key[0], "source": key[1], "mean_solve_time_s": mean, "timeout_count": timeouts[key]})
    return summary


def _markdown_table(summary: list[dict[str, Any]]) -> str:
    lines = [
        "| Grid size | Source | Mean solve time (s) | Timeouts |",
        "|---:|---|---:|---:|",
    ]
    for row in summary:
        mean = "TIMEOUT" if row["mean_solve_time_s"] is None else f"{row['mean_solve_time_s']:.6g}"
        lines.append(f"| {row['size']}x{row['size']} | {row['source']} | {mean} | {row['timeout_count']} |")
    return "\n".join(lines)


def _plot(summary: list[dict[str, Any]], out: Path) -> None:
    by_source: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in summary:
        if row["mean_solve_time_s"] is not None:
            by_source[row["source"]].append((row["size"], row["mean_solve_time_s"]))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for source, points in sorted(by_source.items()):
        points = sorted(points)
        ax.plot([p[0] for p in points], [p[1] for p in points], marker="o", label=source)
    ax.set_xlabel("Grid size N for NxN board")
    ax.set_ylabel("Mean solve time (s)")
    ax.set_yscale("log")
    ax.grid(True, which="both", linestyle=":", linewidth=0.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()

