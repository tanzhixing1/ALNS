# Stage 2D Cascade Repair Pre-Implementation Audit

Baseline and current commit: `74891482523fa8a0ef15b5ef9143d3252d5250d0`.

Formal paper source: `论文-一审改稿_0424tzx.pdf`, Sections 5.1.2, 5.1.3, and 5.1.5, pages 31-34, Equations (93), (95), and Algorithm 1.

The paper explicitly defines Multi-node Cascade Repair as joint reconstruction of dependency bundles formed from the Cascade Removal set. Current code instead tries a limited bundle strategy and then repairs all remaining `unassigned` customers through generic `_all_moves`; it can also consume stale/missing metadata and globally consolidate unrelated sorties.

The current removal operator passes only `cascade_removed: List[int]` and `cascade_bundles: List[List[int]]`. It does not pass the associated route segments, sortie snapshots, truck/warehouse relations, carrier/launch/recovery context, or dependency order needed for the paper-level repair.

Final decision: **STAGE 2D BLOCKED BY REMOVAL INPUT**.

## Files

- `00_environment.md`: baseline, worktree guard, tests, and probes.
- `01_paper_source_index.md`: formal and engineering sources.
- `02_paper_cascade_repair_semantics.md`: direct answers to the paper-semantics questions.
- `03_paper_quotes_and_evidence.md`: page-level excerpts and evidence limits.
- `04_current_code_call_graph.md`: registry, ALNS path, and full helper graph.
- `05_current_cascade_repair_behavior.md`: actual implementation behavior.
- `06_bundle_data_flow.md`: removal metadata, missing context, and staleness.
- `07_bundle_external_effects.md`: active structural changes versus passive propagation.
- `08_paper_code_gap_matrix.md`: required classification/action matrix.
- `09_stage2d_vs_stage2f_boundary.md`: repair/removal ownership.
- `10_alignment_questions.md`: only unresolved implementation choices.
- `11_stage2d_implementation_readiness.md`: readiness decision and controlled next steps.

No production code, test, config, checker, objective, registry, ALNS loop, or commit was changed.
