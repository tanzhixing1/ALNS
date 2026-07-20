# Focused Audit Test Results

- Audit probe syntax: PASS.
- Heavy clean/instrumented semantic oracle: PASS.
- Small clean/instrumented semantic oracle: PASS.
- Solver clean/instrumented action/final-State oracle: PASS.
- Dynamic van/same-van/cross-van/high-floor/boundary/linked candidates: PASS;
  false negatives 0.
- Focused pytest command: Stage 2C True Regret-2, Stage 2B Local/Global,
  Stage 2A checker differential, State.copy/context isolation, Cascade isolation,
  strict checker, cross-van timing and high-floor construction.
- Pytest result: **62 passed in 10.81 s**, 0 failed.
- Full 294-node suite: intentionally not rerun per Stage 2G.0 scope.

`pytest` was run and passed. The generated coverage XML is retained under this
audit's `raw/` area only; no tracked test, expectation or fixture changed.
