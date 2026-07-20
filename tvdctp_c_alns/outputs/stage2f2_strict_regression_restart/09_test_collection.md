# Test Collection

Command: bundled Python `-m pytest --collect-only -q` with repository addopts/cache disabled.

- Total: 294
- Non-medium (`-k 'not medium'`): 293
- Medium (`-k 'medium'`): 1
- Stage 2D files: 58
- Stage 2E files: 115
- Stage 2F file: 19

The only medium node is:

`tests/test_regression_rules.py::test_regression_model_rules_across_scales[medium]`

The increase from the prior 292 total / 17 Stage 2F count is exactly the two approved paper/extended Action 15 parameter cases added in Stage 2F.1.1.
