# Full test coverage

## Collection and focused groups

- Final collection: 221 nodes, 0 collection errors.
- A.2 focused: 33 passed.
- A.2 + A.1 + complete Stage 2D focused group: 119 passed in 49.88s.

## Full-suite attempt

`python -m pytest tests -q --durations=30` printed exactly 22 passing dots and
timed out after 900.8 seconds. This matches the A.1 full-suite position and is
not reported as `FULL SUITE PASS`.

## Mutually exclusive final groups

| Group | Selection | Nodes | Result |
| --- | --- | ---: | --- |
| A | `python -m pytest tests -q -k "not medium" --durations=30` | 220 | 220 passed, 1 deselected, 5 warnings in 300.79s |
| B | exact `test_regression_model_rules_across_scales[medium]` | 1 | timed out after 901.1s; no assertion traceback |

The groups have zero overlap and their union is all 221 collected nodes. Group
B is not called a pass. It reproduces the same single-node A.1 environment
baseline (about 901 seconds) while every other old and new node passes.

## Decision

**BASELINE-RELATIVE GROUPED REGRESSION PASS**

- Passed outside the established baseline hang: 220.
- Failed: 0 observed.
- New timeouts: 0.
- Warnings: 5, unchanged.
- Full-suite pass claimed: NO.
