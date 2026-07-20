# RNG and Determinism

The 16-pair matrix ran twice. All recorded stable fields matched for all 16 pairs: eligibility, RNG inputs/results, requested count, selection, graph, closure, R*, partition/order, actual unassignment, Path B result, objective, feasibility/violations, fingerprint, checker/objective counts, and context status.

Native contract:

- one `choice(..., replace=False)` seed call when eligible;
- zero graph, closure, partition, snapshot, Path B, removal, and checker RNG calls;
- Action 15 repair RNG unchanged before/after in both modes.

Four non-trivial fixed-point fixtures also matched across their two runs, and paper-mode deterministic tests passed for seeds 17, 29, and 41.

```text
DETERMINISM PASS
```
