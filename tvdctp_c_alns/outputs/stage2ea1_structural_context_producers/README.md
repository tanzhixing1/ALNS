# Stage 2E-A.1 Universal RemovalStructuralContext Producers

This directory records the behavioral baseline, design, implementation
evidence, regression results, scope audit and final gate decision for Stage
2E-A.1.

## Index

- `00_preimplementation_baseline.md`: four-destroy and 16-pair business baseline.
- `00a_current_environment_test_baseline.md`: reproducible Step 0 test baseline.
- `01_context_schema.md` through `04_producer_capabilities.md`: immutable schema, projection, authoritative footprint and producer contract.
- `05_destroy_equivalence.md` through `11_three_pairs_still_blocked.md`: strict behavioral, lifecycle, isolation, Cascade and pair evidence.
- `12_determinism_runs.csv`: three independent fixed-seed runs per destroy.
- `13_focused_test_results.txt`: focused commands and results.
- `14_full_test_coverage.md`: 188-node full/grouped coverage and known baseline hang.
- `15_scope_diff_review.md`: file-by-file and protected-scope audit.
- `16_gate_decision.md`: complete gate table and final decision.

The context is repair-agnostic and ephemeral. It is present only on the
disposable destroyed candidate and is consumed/cleared at every public repair
boundary. Existing 13 compatible pairs are unchanged; the three ordinary
destroy plus Cascade repair pairs remain blocked for Stage 2E-A.2.

Final status: **STAGE 2E-A.1 COMPLETE — STAGE 2E-A.2 READY**.
