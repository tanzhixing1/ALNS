# Stage 2E-A.2 Ordinary Cascade Adapter

This directory records representability, architecture, strict behavior,
performance isolation, regression coverage, scope and final gate evidence for
the deterministic ordinary-removal-context to native-Cascade-bundle adapter.

## Index

- `00_representability_gate.md`: mandatory pre-code representability decision.
- `01_adapter_architecture.md`–`08_adapted_contract_schema.md`: adapter facts,
  graph/order rules, lifecycle, boundary and reused contract schema.
- `09_native_cascade_bypass.md`–`11_existing_13_pair_regression.md`: native and
  pair equivalence evidence.
- `12_performance_isolation.md` / `13_performance_runs.csv`: A.1/A.2 medians
  and all 16 A.2 pairs repeated three times.
- `14_cascade_strict_regression.md` / `15_16_pair_matrix.md`: strict native
  evidence and final A=10, B=6, C=0, D=0 matrix.
- `16_determinism_runs.csv`: three exact runs for each newly unlocked pair.
- `17_focused_test_results.txt` / `18_full_test_coverage.md`: focused and
  baseline-relative grouped pytest evidence.
- `19_scope_diff_review.md` / `20_gate_decision.md`: protected-scope audit and
  final gate table.

The adapter executes only for Random/Greedy/Related + Cascade. Native Cascade
bypasses it, all other repairs discard the raw context without adaptation, and
no fallback, paper mode, registry, Stage 2F or performance optimization was
introduced.

Final status: **OPERATOR PAIR CONTRACT PASS — STAGE 2E-A.2 COMPLETE — STAGE 2E.1 READY**.
