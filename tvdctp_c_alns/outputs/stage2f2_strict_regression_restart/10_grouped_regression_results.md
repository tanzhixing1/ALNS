# Grouped Regression Results

| Group | Collected | Result | Runtime |
|---|---:|---|---:|
| Stage 2D bundle contract | 18 | 18 passed | 0.54 s |
| Stage 2D Cascade repair + multi-drone | 40 | 40 passed | 3.80 s |
| Stage 2E-A.1 context lifecycle | 28 | 28 passed | 2.05 s |
| Stage 2E-A.2 ordinary adapter | 33 | 33 passed | 4.79 s |
| Stage 2E.1 operator mode | 54 | 54 passed | 7.11 s |
| Stage 2F.0 deterministic fixtures | 4×2 | all four run-pairs identical | 2.3 s wall |
| Stage 2F.1 file | 19 | 19 passed | 6.28 s |
| Stage 2F.1 focused boundary | 83 | 83 passed | 21.01 s |
| Full non-medium | 293 | 293 passed; 1 deselected; 5 expected warnings | 68.77 s |
| Medium | 1 | 1 passed | 397.85 s |

The medium node completed naturally with no timeout, traceback, or failure. Historical Stage 2E.1 evidence recorded the same node exceeding an approximately 901-second external window; this restart completed it in 6:37.

All 294 collected nodes passed through disjoint non-medium + medium execution. A single one-shot 294-node command was not run because the contract requires the medium node to run separately; grouped complete-suite coverage is claimed.

No failed pytest nodes. The only nonzero command was the intentionally invalid CLI spelling `--operator_mode`, which correctly failed fast and was followed by the canonical `--operator-mode paper_mode` smoke.

```text
NON-MEDIUM REGRESSION PASS
MEDIUM SUITE PASS
GROUPED FULL-SUITE COVERAGE PASS
```
