# Stage 2F.2 Strict Regression — Full Restart

## Outcome

All mandatory gates passed from baseline `172166eea9e34ae5551302d4bfa1cdb62ebc479b` without production, test, or expectation changes.

- Prerequisites: 83 focused, 2 exact, 2 Action 15, 6 direct — all passed.
- Paper matrix: A=10, B=6, C=0, D=0; all 16 deterministic across two runs.
- Ordinary: 12/12 exact; no RNG, adapter or context drift.
- Native: 4/4 attributed; ordinary adapter calls zero.
- Action 15: paper iteration 7 / seed `[7,14]`; extended iteration 8 / seed `[11,7]`; each has one raw snapshot, one canonical rejection, zero scoring and atomic rollback.
- Tests: 294 collected; 293/293 non-medium passed; 1/1 medium passed in 397.85 s.
- Main: default and explicit canonical paper mode completed, best `811.9529412450966`, feasible, zero violations, identical history/actions.
- Git: HEAD unchanged; tracked/staged/production/test diff zero.

```text
PAPER 16-PAIR CONTRACT PASS
ORDINARY 12-PAIR ISOLATION PASS
NATIVE FOUR-PAIR ATTRIBUTION PASS
ACTION-15 APPROVED CONTROL FLOW PASS
NATIVE/ADAPTER BOUNDARY PASS
CONTEXT LIFECYCLE PASS
ATOMIC FAILURE CONTRACT PASS
NON-MEDIUM REGRESSION PASS
MEDIUM SUITE PASS
SMALL MAIN SMOKE PASS
KNOWN CONSERVATIVE REPRESENTATION GAPS PRESERVED
STAGE 2F.2 COMPLETE
STAGE 2 FINAL AUDIT READY
STAGE 2G HELD
NO_COMMIT_REQUIRED
```

Stage 2 Final Audit was not executed. No final paper-baseline freeze is claimed.

## Required evidence

- `00_git_gate.md`
- `01_prerequisite_contract_recheck.md`
- `02_paper_16_pair_matrix.md` / `02a_paper_16_pair_matrix.csv`
- `03_ordinary_12_pair_baseline_comparison.md` / `03a_ordinary_12_pair_diff.csv`
- `04_native_four_pair_attribution.md` / `04a_native_four_pair_trace.csv`
- `05_native_adapter_boundary.md`
- `06_context_lifecycle_and_atomicity.md`
- `07_rng_and_determinism.md`
- `08_operator_mode_and_registry.md`
- `09_test_collection.md`
- `10_grouped_regression_results.md` / `10a_grouped_regression_results.csv`
- `11_small_main_smoke.md`
- `12_frozen_component_review.md`
- `13_representation_gap_regression.md`
- `14_stage2_final_audit_readiness.md`
- `15_scope_diff_review.md`
- `16_gate_decision.md`

Raw reproducibility evidence includes both Action 15 JSON traces, the two-run 16-pair JSON, the output-only pair probe, and default/explicit main artifacts.
