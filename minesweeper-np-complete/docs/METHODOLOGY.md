# Methodology

## Why Played-Game Boards

The benchmark's primary instances come from actual Minesweeper play rather than uniformly random revealed grids. A played game creates structure: the first click tends to open a low-number region, flood-fill creates connected open areas, and later clues concentrate around a frontier between known and unknown cells. These correlations are exactly the structure a human or deterministic bot sees in practice.

Uniform-random instances are still generated as a secondary comparison group. They use uniform mine placement and reveal random safe cells without simulating play. Reporting both sources helps identify whether realistic game structure changes the difficulty profile of the SAT instances.

## Safe First Click

`generate_board` samples mines uniformly from every cell except the first clicked cell and its eight neighbors. This is the standard safe-first-click convention used by mainstream Minesweeper implementations: the opening click should not immediately lose, and it should usually expose a small local region rather than an isolated clue. The selected first-click cell and the RNG seed determine the protected region reproducibly.

## Stuck States

The no-guess bot starts from the first click and repeatedly applies the two single-point clue rules:

1. If a revealed clue's remaining unrevealed neighbors must all be mines, mark those cells as known mines.
2. If a revealed clue already has all required adjacent mines marked, reveal every other unrevealed neighbor as safe.

The bot iterates these rules to a fixed point. A stuck state is a partially revealed board where at least one safe cell remains hidden and a full fixed-point pass produces no new forced safe cells or forced mines. This is a natural benchmark snapshot because local play can no longer proceed; a player would need to guess or apply more global reasoning. MCP asks whether any covered-cell mine assignment is consistent with the revealed clues, so these stuck states are precisely the kind of mid-game consistency questions we want to measure.

If the bot solves a board without getting stuck, the generator stores the earliest snapshot at the configured fallback reveal fraction, defaulting to 0.4. That keeps small or easy boards in the benchmark without fabricating a stuck state.

## Encoding

Each covered cell becomes one Boolean variable. For every open clue cell, the encoder gathers its covered neighbors and adds a pseudo-Boolean equality requiring their sum to match the clue value. The implementation uses `pysat.pb.PBEnc.equals`; the resulting clauses are solved with PySAT's Glucose4 wrapper (`g4`). Encoding time and solve time are measured separately.

## Measurement

`run_benchmark.py` writes three artifacts per run:

- `raw.jsonl`, one full result record per instance.
- `summary.csv`, grouped by grid size and source.
- `run_info.json`, with timestamps, machine information, package versions, Python version, git commit hash, and CLI arguments.

The benchmark is resumable. If `raw.jsonl` already contains an `instance_id`, rerunning the command with the same output directory skips that instance instead of solving it again.

## Limitations

The no-guess bot intentionally uses only single-point local deductions. It does not implement subset reasoning, pattern libraries such as 1-2-1, probability estimates, or full SAT-based inference. Therefore some "stuck" states may still be solvable by a stronger human or solver without guessing. This is acceptable for the benchmark: the goal is not to model perfect human play, but to produce realistic mid-game MCP instances whose revealed clues came from actual game dynamics.

Uniform-random comparison boards do not model player behavior and should not be treated as the primary empirical claim. They are useful as a control group only.

Wall-clock solve times depend on hardware, OS scheduling, and Python/PySAT build details. SAT/UNSAT verdicts and generated instance files should be reproducible with the same seed and metadata. Paper numbers should be tied to a specific documented machine and committed result directory.

Timeouts are recorded as `TIMEOUT` results rather than failures. A timeout at larger sizes is an informative benchmark outcome, consistent with the expected hard instances in an NP-complete decision problem.

