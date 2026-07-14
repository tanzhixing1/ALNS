# Stage 2D final candidate-coverage gate

Baseline commit: `999ba977f6ea36d7bcf02a665accc56f312e11c4`

| Gate | Result | Evidence |
| --- | --- | --- |
| Drone symmetry classified | PASS | `01_drone_symmetry_analysis.md`: B, NOT STRICTLY SYMMETRIC |
| First-drone safety proven or fixed | PASS | First-only selection removed from both repair candidate loops |
| Non-first feasible drone found | PASS | Real warehouse-return counterexample and focused test 2 |
| Existing-task case covered | PASS | Focused test 3 |
| Current-carrier case covered | PASS | Focused test 4 |
| Cross-van case covered | PASS | Focused test 5 and existing regressions |
| Stage 2C coverage correct | PASS | Focused test 6; 20 Stage 2C tests passed |
| Stage 2D coverage correct | PASS | Focused test 7; Stage 2D.0/2D.1 tests passed |
| Candidate identity includes drone ID | PASS | Distinct identity assertion and concrete ID retained in sortie State |
| No unsafe symmetry pruning | PASS | Every concrete candidate reaches unchanged hard feasibility |
| No lossy candidate truncation | PASS | No top-K, beam, cutoff, or cost deduplication |
| Omega(B) implementation choice documented | PASS | `06_omega_bundle_scope_statement.md` |
| Candidate counts consistent | PASS | `unique <= feasible <= raw`; 9/9/9 and 100/100/100 |
| Deterministic | PASS | Three identical count/objective/fingerprint runs |
| Full pytest | PASS | 160 passed, 5 warnings in 1511.42s |
| Scope clean | PASS | Only authorized repair enumeration, tests, and reports changed |
| Worktree valid | PASS | `git diff --check`; clean status verified after commit |

The warnings are the existing expected RuntimeWarnings from negative
initial-solution regression cases; no warning originates in this change.

## Decision

**STAGE 2D FINAL CLOSED**

**STAGE 2E READY**

This decision records readiness only. No Stage 2E, Stage 2F, or Stage 3 work was
implemented.
