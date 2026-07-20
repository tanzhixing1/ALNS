# Stage 2F.0 Cascade-aware Removal Paper Audit

## Outcome

This audit established the strongest contract supported by the primary paper and compared it to the production Native Cascade path without modifying production or tests.

Final result:

```text
CASCADE REMOVAL PAPER CONTRACT PARTIAL
MINIMAL ENGINEERING DECISIONS REQUIRED
CASCADE REMOVAL PAPER GAP CONFIRMED
STAGE 2F.0 COMPLETE
STAGE 2F.1 CONDITIONALLY READY — NATIVE REMOVAL CORRECTION REQUIRED
```

The paper explicitly defines recursive closure, fixed-point termination, final `R*`, and simultaneous removal. It partially defines structural dependency and dependency-based bundles, but does not fully define the exact dependency graph, standalone Cascade seed generator, component algorithm, bundle/customer order, ties, or RNG call sequence.

Production has an aligned fixed-point control loop, but its `D_i` is limited to one matching drone sortie and non-warehouse anchors. It does not discover the broader associated truck/van/coordination customer dependencies named by the paper. Its per-sortie bundle construction is not a general dependency partition and can overlap for shared structures. These are the narrow Stage 2F.1 targets; repair and infrastructure remain frozen.

## Key evidence

- Git baseline: `760e3bc445b04fd2673c81774c90d30422f890df`; tracked/staged diff zero.
- Primary PDF visually inspected at pages 16–18.
- Main paper anchors: p.17 formula (93), p.17 formula (95), p.18 Algorithm 1.
- Current behavior: four canonical small-fixture cases, each repeated twice with the same seed.
- Determinism: every required observed field matched within each pair.
- Focused existing tests: `22 passed in 3.37s`.
- No commit, no Stage 2F.1 implementation, no performance work.

## Required reports

- `00_git_gate.md`
- `01_paper_evidence_matrix.md`
- `01a_paper_evidence_matrix.csv`
- `02_native_cascade_call_graph.md`
- `02a_function_inventory.csv`
- `03_current_behavior_snapshot.md`
- `03a_current_behavior_snapshot.csv`
- `04_paper_implementation_gap_matrix.md`
- `04a_gap_matrix.csv`
- `05_rng_semantics_audit.md`
- `06_stage2f1_implementation_contract.md`
- `07_stage2f2_regression_plan.md`
- `08_stage2_final_audit_readiness.md`
- `09_risk_register.md`
- `10_scope_diff_review.md`
- `11_gate_decision.md`

## Raw/visual audit evidence

- `current_behavior_raw.json`: eight production-function runs and pairwise determinism results.
- `current_behavior_probe.py`: audit-only probe; not imported by production.
- `paper_pdf_page_16.png`, `paper_pdf_page_17.png`, `paper_pdf_page_18.png`: direct page renders used for visual inspection.
- `pdf_page_renderer.mjs`: audit-only renderer; the PDF itself was not copied to outputs.

## Definition levels

- EXPLICIT: recursive propagation, closure termination, final `R*`, multi-chain union.
- PARTIAL: seed/quantity/randomness, dependency definition/direction, related routes/sub-routes, bundle partition, duplicates.
- UNSPECIFIED: within-bundle dependency order, tie-breaking, infeasible-expansion handling.

## Current Native Cascade summary

- Seed: one uniform sample without replacement from sorted van+drone served customers.
- Expansion: matching sortie customers plus non-warehouse launch/recovery nodes.
- Final set: fixed point over that limited predicate.
- Bundles: sortie intersections in State order, then singleton leftovers.
- `dependency_order`: sorted bundle membership, explicitly paper-unspecified.
- RNG: one call when served customers exist; no closure/partition/context/repair RNG.
- Determinism: yes on the audited baseline/fixtures; cross-runtime set-order risk remains.

## Engineering infrastructure effect

`RemovalStructuralContext`, pre-removal snapshots, ordinary adapter, lifecycle cleanup, and action registry do not consume Native RNG or independently change Native seed/closure. Native bypasses the ordinary adapter. Paper mode remains the frozen 16 actions and Native Cascade + Cascade remains action 15.

## Remaining blockers before final baseline freeze

1. Implement only the conditional Stage 2F.1 Native dependency/closure/partition contract.
2. Execute the Stage 2F.2 semantic and deterministic regression plan.
3. Reconfirm repair/objective/checker/State/SA/weights and all 16 pairs are unchanged.
4. Complete the small reference and multi-seed readiness work in the final audit.

Stage 2G, PPO, and Stage 3 remain deferred.

