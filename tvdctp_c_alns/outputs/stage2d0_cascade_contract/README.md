# Stage 2D.0 Cascade Input Contract

This directory contains the paper clarification, preimplementation audit, structured destroy-to-repair contract, implementation evidence, test logs, scope review, and Stage 2D.1 readiness decision.

## Index

- `00_environment.md`
- `01_paper_joint_repair_clarification.md`
- `02_preimplementation_contract_audit.md`
- `03_cascade_bundle_contract.md`
- `04_complexity_risk_and_canary_plan.md`
- `05_implementation_design.md`
- `06_snapshot_capture_evidence.md`
- `07_removal_equivalence.md`
- `08_metadata_lifecycle.md`
- `09_focused_test_results.txt`
- `10_full_pytest_result.txt`
- `11_scope_diff_review.md`
- `12_stage2d1_readiness.md`

## Final terminal summary

```text
Stage 2D.0 Cascade Input Contract

Baseline commit: 74891482523fa8a0ef15b5ef9143d3252d5250d0
Actual starting HEAD: 9c584a514a3aba68e68a7570f6741ff9979d7816
New commit: see the Stage 2D.0 commit in `git log` and the final terminal summary

Paper joint repair meaning:
- Full Cartesian required: NO; generation of Ω(B) is Paper unspecified
- Dependency-order reconstruction: Paper unspecified
- Affected-route restriction: associated structures named; exact boundary Paper unspecified
- Full objective selection: YES, f(S ⊕π B)
- Paper bundle-size evidence: No explicit bundle-size evidence was found

Bundle contract:
- customer IDs: YES
- dependency order: current implementation order; Paper unspecified
- route snapshots: bounded affected segments
- sortie snapshots: associated pre-removal sub-routes
- launch/recovery: nodes, vans, positions, same/cross status
- carrier: initial/launch/recovery carrier and transfer
- allowed repair scope: affected_structure_scope

Snapshot captured before removal: YES
Removal customer set changed: NO
Bundle partition changed: NO
Random call order changed: NO
Cascade repair changed: NO
Checker changed: NO
Objective changed: NO
ALNS main loop changed: NO
Top-K / beam added: NO
Full State snapshot fallback used: NO

Metadata lifecycle: PASS
State.copy isolation: PASS
Determinism: PASS
Focused tests: PASS
Full pytest: PASS
git diff --check: PASS
Tracked worktree: CLEAN AFTER COMMIT

Complexity plan:
- hard canaries: bundle/affected-structure/strategy/copy/objective/checker/depth counts
- soft timing metrics: enumeration/scoring/bundle-repair time
- lossy pruning used: NO

Final decision:
STAGE 2D.1 IMPLEMENTATION NEEDS ALIGNMENT

Alignment / blocking reasons:
- Ω(B) generation/exhaustiveness is Paper unspecified
- bundle and bundle-internal order are Paper unspecified
- exact affected-segment boundaries, tie-break, empty-candidate policy, and fallback are Paper unspecified
```
