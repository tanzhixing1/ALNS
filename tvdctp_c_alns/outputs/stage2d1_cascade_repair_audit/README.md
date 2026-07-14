# Stage 2D.1 Bundle-scoped Cascade Repair + Stage 2D.2 Gate

Baseline: `1b3400ff329f46cc03a85b030614964553c2467c`

This directory records the mandatory Git provenance Gate, preimplementation audit, bundle strategy design, stable identity and exact ties, canonical partial validation, affected-scope protection, atomic failure, focused/full tests, determinism, complexity canaries, scope review, and final Stage 2D Gate.

## Index

- `00_git_provenance.md`
- `01_preimplementation_code_audit.md`
- `02_bundle_reconstruction_design.md`
- `03_strategy_identity_spec.md`
- `04_partial_validation_design.md`
- `05_bundle_scope_and_external_effects.md`
- `06_atomic_failure_design.md`
- `07_focused_test_results.txt`
- `08_full_pytest_result.txt`
- `09_determinism_runs.csv`
- `10_exact_tie_determinism.md`
- `11_complexity_canaries.md`
- `12_scope_diff_review.md`
- `13_stage2d_gate_decision.md`

## Terminal result

```text
Git provenance: GIT PROVENANCE PASS
Focused Stage 2D.1 tests: 33 passed
Stage 2D.0 contract: 18 passed
Stage 2B Local: 10 passed
Stage 2C Regret: 20 passed
Cross-van focused: 5 passed
Full pytest: 153 passed, 5 warnings
Fixed-seed deterministic runs: PASS (3/3)
Hard complexity canaries: PASS
Lossy pruning used: NO
Final decision: STAGE 2D COMPLETE
```

Stage 2E, Stage 2F, and Stage 3 were not entered.
