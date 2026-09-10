from __future__ import annotations

from mcp_bench.generate_instances import generate_played_game_instance
from mcp_bench.instance import BoardInstance


def test_same_seed_produces_byte_identical_serialization() -> None:
    kwargs = {
        "rows": 10,
        "cols": 10,
        "seed": 42,
        "source_index": 0,
        "mine_density": 0.16,
        "fallback_reveal_fraction": 0.4,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "git_commit": "abcdef",
    }
    first = generate_played_game_instance(**kwargs).to_json()
    second = generate_played_game_instance(**kwargs).to_json()
    assert first == second
    assert BoardInstance.from_json(first).to_json() == first

