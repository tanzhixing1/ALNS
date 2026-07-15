# Current environment test baseline

Baseline commit: `e5d6ca16beb2dea928cbf2717352edf408d141c6`.

## Runtime discovery

- Default `python`: `C:\Users\19088\.agent-reach-venv\Scripts\python.exe`
  (Python 3.12.13), but that environment has no pytest.
- README venv: `D:\STUDY\STUDY\PythonProject\.venv`, but its interpreter
  target no longer exists and it cannot create a process.
- Working project runtime:
  `C:\Users\19088\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
- Pytest: 9.1.1 on Python 3.12.13; coverage plugin enabled by repository
  `pyproject.toml`.

## Collection

Command: `python -m pytest --collect-only -q`

- Collected: **160 nodes** in 5.04 seconds.
- Collection errors: **0**.
- Test files:
  - `tests/test_core_model_capabilities.py`
  - `tests/test_regression_rules.py`
  - `tests/test_stage1_drone_generator.py`
  - `tests/test_stage2a_drone_feasibility.py`
  - `tests/test_stage2b_local_greedy.py`
  - `tests/test_stage2c_regret2.py`
  - `tests/test_stage2d_multidrone_coverage.py`
  - `tests/test_stage2d0_cascade_contract.py`
  - `tests/test_stage2d1_cascade_repair.py`

## Full-suite attempt

Command: `python -m pytest -vv --durations=30`

- Result: **timeout after 901.5 seconds; not a PASS**.
- The first 22 nodes passed: all 20 nodes in
  `test_core_model_capabilities.py` plus the tiny and small parametrizations in
  `test_regression_rules.py`.
- Execution was still inside
  `test_regression_model_rules_across_scales[medium]` when the tool terminated.
- Assertion failure traceback before timeout: none.

The suspected node was then run alone with the same repository pytest config:

`python -m pytest -vv --durations=30 tests/test_regression_rules.py::test_regression_model_rules_across_scales[medium]`

- Collected: 1.
- Result: **timeout after 901.5 seconds; not a PASS**.
- Assertion failure traceback: none.
- Classification: repeatable baseline hanging/very-slow test, not an A.1
  regression and not counted as passed.

## Mutually exclusive grouped coverage

| Group | Selected | Passed | Failed | Warnings | Wall time / result |
| --- | ---: | ---: | ---: | ---: | --- |
| `test_regression_rules.py -k "not medium"` | 25 | 25 | 0 | 5 | 194.45s pytest / 199.1s process |
| `test_core_model_capabilities.py` | 20 | 20 | 0 | 0 | 57.97s pytest / 60.996s process |
| `test_stage1_drone_generator.py` | 1 | 1 | 0 | 0 | 7.44s / 9.526s |
| `test_stage2a_drone_feasibility.py` | 25 | 25 | 0 | 0 | 3.31s / 5.565s |
| `test_stage2b_local_greedy.py` | 10 | 10 | 0 | 0 | 3.02s / 4.974s |
| `test_stage2c_regret2.py` | 20 | 20 | 0 | 0 | 8.18s / 10.620s |
| `test_stage2d_multidrone_coverage.py` | 7 | 7 | 0 | 0 | 5.05s / 7.412s |
| `test_stage2d0_cascade_contract.py` | 18 | 18 | 0 | 0 | 3.44s / 5.329s |
| `test_stage2d1_cascade_repair.py` | 33 | 33 | 0 | 0 | 16.76s / 18.783s |
| medium node alone | 1 | 0 | 0 | 0 | timeout at 901.5s |

Coverage arithmetic: `25+20+1+25+10+20+7+18+33+1 = 160`.
The groups are mutually exclusive: the medium node is deselected from its file
group and appears only in the individual diagnostic group. No node is omitted
or counted twice.

## Slowest completed baseline tests

- regression small: 124.94s.
- core two-container cache integration smoke: 53.73s.
- regression tiny: 36.42s.
- tiny multi-van resource model: 22.29s.
- route-plan detail output: 4.27s.
- Stage 2D.1 multiple-bundle deterministic run: 3.96s.
- Regret fixed-seed three-run test: 3.20s.

The five warnings are the existing expected `RuntimeWarning` cases for
controlled initial-solution assignment failures in
`test_regression_rules.py`.

## Baseline decision

Current full-suite PASS is **not** claimed. The environment satisfies the
task's condition B: one repeatable baseline hanging node is isolated, and a
reproducible mutually exclusive plan covers every collected node. Production
implementation may proceed, but post-change evidence must compare the same
medium node separately and must not report its timeout as PASS.
