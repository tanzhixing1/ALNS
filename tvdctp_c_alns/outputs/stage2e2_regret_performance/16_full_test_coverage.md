# Test Coverage

- Collection: `275 tests collected in 3.78s`.
- Unpartitioned full suite: timed out after `1201.3s` at 22 completed nodes, with no
  failure output; the active next node was the known medium parameter.
- A first grouping command used an incomplete deselect node id and reproduced the
  same timeout pattern; it is not counted as the non-medium result.
- Correct baseline-relative group, excluding exactly
  `tvdctp_c_alns/tests/test_regression_rules.py::test_regression_model_rules_across_scales[medium]`:
  `274 passed, 1 deselected, 5 warnings in 205.52s`.
- The medium node remains the same known long-running node and was not completed.

Result: **BASELINE-RELATIVE GROUPED REGRESSION PASS**.

`FULL SUITE PASS` is **not** claimed.
