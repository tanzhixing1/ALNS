# Stage 2E.2 True Regret-2 Performance Optimization

This directory records the baseline extraction, duplicate-work audit, evaluated
repair-local exact-cache prototype, semantic evidence, performance measurements,
regression coverage, and final gate decision.

The prototype preserved the focused business result but achieved only a
`6.775417849251609%` median wall reduction and `3.468354430379747%` combined actual
objective/checker evaluation reduction. Both are below the required thresholds.
It was fully reverted; production code remains at baseline semantics with no Stage
2E.2 cache accepted.

Required conclusion:

```text
STAGE 2E.2 PERFORMANCE TARGET NOT MET
STAGE 2F HELD
```

No 20/40/80 optimized gate run and no commit were performed.

`preimplementation_duplicate_audit.json` and `optimized_focused_runs.json` are raw
measurement evidence. The two probe scripts are historical harnesses; the optimized
probe targets the reverted prototype and is not an executable final-production test.
