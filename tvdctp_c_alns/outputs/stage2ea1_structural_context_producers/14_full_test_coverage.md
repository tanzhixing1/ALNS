# Full test coverage

## Collection

- Starting baseline `e5d6ca16beb2dea928cbf2717352edf408d141c6`: 160 nodes, 9 files, 0 collection errors.
- Stage 2E-A.1 worktree: 188 nodes, 10 files, 0 collection errors.
- Difference: exactly 28 new Stage 2E-A.1 focused nodes.

## Full-suite attempt

`python -m pytest -q` did not complete within the 900-second tool limit. It
printed 22 passing dots and then timed out after 901.6 seconds. This is **not**
reported as `FULL SUITE PASS`.

The starting baseline full run stopped at the same location: after the first
22 passing nodes, the runner entered
`tests/test_regression_rules.py::test_regression_model_rules_across_scales[medium]`
and timed out after 901.5 seconds without a failure traceback.

## Mutually exclusive grouped coverage

| Group | Selection | Covered nodes | Result | Time |
| --- | --- | ---: | --- | ---: |
| A | `python -m pytest -q -k "not medium" --durations=30` | 187 | 187 passed, 1 deselected, 5 warnings | 300.87s |
| B | exact `test_regression_model_rules_across_scales[medium]` node | 1 | timed out; no assertion traceback | 901.4s |

The groups have zero overlap and their union is all 188 collected nodes.
Group B is not called a pass. Its observed behavior is, however, identical to
the repeatable preimplementation environment baseline: the same single node
remained active past the same 900-second limit, while every other baseline
node and every new node completed successfully.

## Decision

**GROUPED COMPLETE COVERAGE PASS** against the established Step 0 baseline-B
procedure. This classification means complete node coverage and no regression
relative to the reproducible environment baseline; it does not mean that the
hanging `medium` node itself passed or that the one-shot full suite completed.

- Full collected: 188.
- Passed outside the known hanging node: 187.
- Failed: 0 observed.
- Known baseline-hanging nodes: 1.
- Warnings: 5, unchanged from baseline.
- Full regression proven relative to the established current-environment
  baseline: **YES**.
