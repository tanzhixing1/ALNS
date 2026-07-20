# Extra-call State Analysis

## Paper

- Call: current 484, iteration 7/action 15.
- State: disposable Cascade repair snapshot candidate, not current/best/final candidate.
- Before fingerprint: `16f567077233b628e82d324c1c1cf27de5bc2a910aeddad54ad6c5b14c616a68`.
- After fingerprint: `14690d8b873af7f09916081518cde065c13f160627870f37610e172ed7509f3b`.
- Unassigned: `[5, 6, 8, 11, 14]` before/after.
- Active structural context: absent (Cascade detached it before repair work).
- Result: infeasible.
- Violations: high-floor customers 8/11/14 require drone service; the five customers remain unassigned.

## Extended

- Call: current 322, iteration 8/action 15.
- State: disposable Cascade repair snapshot candidate.
- Before fingerprint: `df008ba8a7c24beae7f9091bfa72611b101e0d41238a727f264ee1d28cc18cbb`.
- After fingerprint: `afa0f65c0049774c0e448326e911013e82d56e6d6c152903f256134218e3438e`.
- Unassigned: `[7, 9, 10]` before/after.
- Active structural context: absent.
- Result: infeasible.
- Violations: high-floor customer 10 requires drone service; the three customers remain unassigned.

## Equivalence and effects

- Previous equivalent check: **none**. Each extra input fingerprint is unique in its mode trace.
- Same State as adjacent baseline check: **no**.
- Why it occurs: current Native removal passes a valid corrected bundle to Cascade, so the pre-existing enumeration boundary validates its one snapshot candidate. Baseline fails contract validation earlier.
- Result consumed: **yes**. `_enumerate_bundle_reconstruction_strategies` rejects the snapshot, produces an empty feasible strategy set, and makes Cascade return failure.
- RNG: unchanged; no draw and identical before/after fingerprint.
- Objective: not invoked by the extra call; objective index remains 234 (paper) / 50 (extended). Total objective count remains frozen.
- Candidate ordering/selection: one new raw candidate reaches validation, but no feasible strategy is scored or selected.
- Solver acceptance/current/best: unchanged on this fixture; the returned action-15 candidate is infeasible in both versions and is rejected.
- Subsequent checker sequence: fully realigns after the one-to-two action-15 block.

Deleting the extra check would remove a result-consuming feasibility boundary and could admit an infeasible snapshot strategy. It is not a redundant duplicate.

