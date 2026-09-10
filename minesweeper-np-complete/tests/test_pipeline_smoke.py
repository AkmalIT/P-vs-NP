from __future__ import annotations

from pathlib import Path

from mcp_bench.generate_instances import main as generate_main
from mcp_bench.report import main as report_main
from mcp_bench.run_benchmark import main as benchmark_main


def test_pipeline_smoke(tmp_path: Path) -> None:
    instances = tmp_path / "instances"
    run = tmp_path / "results" / "run_smoke"
    generate_main(
        [
            "--sizes",
            "5",
            "--games-per-size",
            "1",
            "--seed",
            "42",
            "--out",
            str(instances),
            "--generated-at",
            "2026-01-01T00:00:00+00:00",
        ]
    )
    benchmark_main(["--instances", str(instances), "--out", str(run), "--timeout", "10"])
    report_main(["--run", str(run)])
    assert (instances / "5x5.jsonl").exists()
    assert (instances / "manifest.json").exists()
    assert (run / "raw.jsonl").exists()
    assert (run / "summary.csv").exists()
    assert (run / "run_info.json").exists()
    assert (run / "summary.md").exists()
    assert (run / "plot.png").exists()

