# Grouped Regression Results

| Group | Result | Detail |
|---|---|---|
| Stage 2D bundle contract | PASS | 18 passed in 3.42 s |
| Stage 2D Cascade repair + multi-drone | PASS | 40 passed in 17.35 s |
| Stage 2E-A.1 structural context | PASS | 28 passed in 10.87 s |
| Stage 2E-A.2 ordinary adapter | NOT RELIED UPON | command launched concurrently; sibling failure prevented a durable independent summary |
| Stage 2E.1 operator modes | FAIL | 52 passed, 2 failed in 30.00 s; reproduced alone |
| Stage 2F.0 determinism fixtures | PASS | 4 fixtures × 2 runs, all pairwise equal |
| Stage 2F.1 focused recheck | PASS | 81 passed in 31.68 s |
| Stage 2F.2 pair probe | PASS | 16 pairs × 2 runs; A=10/B=6/C=D=0 |
| Full non-medium | NOT RUN | stopped at confirmed grouped non-medium failure |
| Medium | NOT RUN | stopped at confirmed grouped non-medium failure |

Confirmed failures:

1. `test_paper_search_work_matches_preimplementation_baseline`: checker calls 910, expected 909.
2. `test_explicit_extended_run_matches_preimplementation_baseline`: checker calls 885, expected 884.

The single-file rerun reproduced both. Earlier assertions in those tests confirmed frozen action sequences, RNG digest, final objective, final business fingerprint, and objective-call count. The Stage 2F.2 contract labels checker call count diagnostic-only, but the existing non-medium suite still fails; no expectation was changed.

Minimal call chain: `test_stage2e1_operator_modes._baseline_run` -> `run_c_alns` -> registered destroy/repair executions -> the solver's profiled `check_solution_feasible` calls. Static diff shows that Stage 2F.1 changed only the Native removal graph/closure/partition/Path B path. It is a plausible inference that approved Native R* work caused the +1 diagnostic call, but this run did not authorize changing the frozen count and therefore does not treat that inference as a passing result.

```text
STAGE 2F.2 REGRESSION BLOCKED
NEW NON-MEDIUM TEST FAILURE
FULL SUITE PASS NOT CLAIMED
```
