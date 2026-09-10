"""Run SAT benchmarks over generated MCP instances."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import psutil

from .instance import BoardInstance
from .solve import solve_instance


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    instances_dir = Path(args.instances)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "raw.jsonl"
    start = datetime.now(UTC)
    wall_start = time.perf_counter()

    completed = _completed_instance_ids(raw_path)
    rows: list[dict[str, Any]] = []
    if raw_path.exists():
        rows.extend(json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line)

    with raw_path.open("a", encoding="utf-8") as raw_file:
        for instance in _load_instances(instances_dir):
            if instance.metadata.instance_id in completed:
                continue
            result = solve_instance(instance, timeout_s=args.timeout)
            record = {
                "instance": instance.to_dict(),
                "metadata": instance.metadata.__dict__,
                "solve": result.to_dict(),
            }
            raw_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            raw_file.flush()
            rows.append(record)
            completed.add(instance.metadata.instance_id)

    summary_rows = _summarize(rows)
    _write_summary(out / "summary.csv", summary_rows)
    end = datetime.now(UTC)
    run_info = {
        "start_timestamp": start.isoformat(),
        "end_timestamp": end.isoformat(),
        "total_wall_time_s": time.perf_counter() - wall_start,
        "git_commit": _git_commit(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "total_ram_bytes": psutil.virtual_memory().total,
        "package_versions": _pip_freeze(),
        "cli_args": vars(args),
    }
    (out / "run_info.json").write_text(json.dumps(run_info, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_instances(instances_dir: Path) -> list[BoardInstance]:
    instances: list[BoardInstance] = []
    for path in sorted(instances_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line:
                instances.append(BoardInstance.from_json(line))
    return instances


def _completed_instance_ids(raw_path: Path) -> set[str]:
    if not raw_path.exists():
        return set()
    return {
        json.loads(line)["metadata"]["instance_id"]
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line
    }


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["metadata"]["size"], row["metadata"]["source"])].append(row)

    summary: list[dict[str, Any]] = []
    for (size, source), group in sorted(groups.items(), key=lambda item: (int(item[0][0].split("x")[0]), item[0][1])):
        solved_times = [row["solve"]["solve_time_s"] for row in group if row["solve"]["result"] != "TIMEOUT"]
        summary.append(
            {
                "size": size,
                "source": source,
                "count": len(group),
                "timeout_count": sum(row["solve"]["result"] == "TIMEOUT" for row in group),
                "mean_solve_time_s": statistics.fmean(solved_times) if solved_times else "",
                "median_solve_time_s": statistics.median(solved_times) if solved_times else "",
                "stddev_solve_time_s": statistics.stdev(solved_times) if len(solved_times) > 1 else 0 if solved_times else "",
                "min_solve_time_s": min(solved_times) if solved_times else "",
                "max_solve_time_s": max(solved_times) if solved_times else "",
            }
        )
    return summary


def _write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "size",
        "source",
        "count",
        "timeout_count",
        "mean_solve_time_s",
        "median_solve_time_s",
        "stddev_solve_time_s",
        "min_solve_time_s",
        "max_solve_time_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=None)
    return parser.parse_args(argv)


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

