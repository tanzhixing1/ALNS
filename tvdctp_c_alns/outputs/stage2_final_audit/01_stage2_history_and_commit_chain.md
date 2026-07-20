# Stage 2 History and Commit Chain

No stage marked complete has an unresolved correctness gate. Historical runtime/performance holds in Stage 2E were explicit diagnostic gates: the rejected Stage 2E.2 prototype was reverted and did not enter this baseline. Later Stage 2F work was authorized against unchanged production semantics except for the narrowly approved Native removal correction.

| Stage | Objective | Final approved commit | Production scope | Test/result | Final status and evidence |
|---|---|---|---|---|---|
| 2A | Close feasibility, timing diagnostics, rollback, and reproducibility baseline | `854f557d097f8dfe3874af5b3871f449a7f5cec0` | checker/diagnostics and solver observability | 72 passed; three deterministic runs | COMPLETE; `stage2a_final_audit/19_stage2b_gate_decision.md` |
| 2B Local | Route-scoped Local repair with legal cross-van recovery | `0feb748dc96104c4ca8d47f900ff904fe303d655` | `operators.py` Local helpers/entry | 82 passed | COMPLETE; `stage2b_local_greedy_audit/11_stage2b_gate_decision.md` |
| 2C Regret | Strategy-level True Regret-2 over concrete insertion moves | `74891482523fa8a0ef15b5f3871f449a7f5cec0` | `operators.py` regret enumerator/scoring | focused + full gate | COMPLETE; `stage2c_regret2_audit/15_stage2c_gate_decision.md` |
| 2D.0 | Structured pre-removal Cascade input snapshots | `1b3400ff329f46cc03a85b030614964553c2467c` | `operators.py`, `state.py` | focused/full PASS | COMPLETE; Stage 2D.1 alignment questions explicitly recorded |
| 2D.1 | Bundle-scoped Cascade repair, exact scoring, atomic failure | `999ba977f6ea36d7bcf02a665accc56f312e11c4` | `operators.py` | 153 passed | COMPLETE; `stage2d1_cascade_repair_audit/13_stage2d_gate_decision.md` |
| 2D coverage | Remove first-drone-only candidate loss | `b886431084f1e2b8cc1db59d13f03f5798d8fa30` | `operators.py` candidate enumeration | focused/full PASS | Stage 2D final closure; `stage2d_multidrone_coverage/12_final_gate.md` |
| 2E audit/design | Paper catalog and structural adapter contracts | `e5d6ca16beb2dea928cbf2717352edf408d141c6` | reports only | static contract gates | COMPLETE design evidence |
| 2E-A.1 | Universal ephemeral removal context producers | `901ee48da0e1d83fb05dcfb9903c91566e3c69fc` | solver/operators/context/State copy hook | 188-node grouped evidence | COMPLETE; A.2 READY |
| 2E-A.2 | Ordinary removal → Cascade adapter | `ddcfd0cc53bba2d65a695710fd2c805f21f7cd99` | `ordinary_cascade_adapter.py`, `operators.py` | 16-pair A=10/B=6/C=D=0 | COMPLETE; E.1 READY |
| 2E.1 | Strict `paper_mode`, explicit `extended_mode`, frozen action identity | `760e3bc445b04fd2673c81774c90d30422f890df` | registry/config/main/solver | 274 non-medium passed; known medium timeout at that stage | COMPLETE; strict mode gate PASS |
| 2E.1-P | Runtime diagnosis | no commit | output-only instrumentation | 80 iterations completed in 2,776.33 s wall | Diagnosis complete; bottleneck identified |
| 2E.2 | Exact Regret performance experiment | no commit; prototype reverted | no final production delta | 6.78% median speedup, below gate | Target not met; performance gap retained, no cache admitted |
| 2F.0 | Primary-paper Native Cascade removal audit | no commit; baseline `760e3bc` | audit only | 22 focused passed | COMPLETE; partial paper contract and correction scope approved |
| 2F.1 | Correct customer dependency graph, ordered closure, weak-component bundles, Path B | `9488139b8920640b47a8a901e32129df0076200f` | Native path in `operators.py` | 81 focused passed initially | COMPLETE; F.2 READY |
| 2F.2A | Root-cause checker +1 delta | no commit | audit only | deterministic paper/extended traces | COMPLETE; correctly held F.2 for an interface decision |
| 2F.1.1 | Approve Action 15 canonical validation reachability and exact checker baselines | `172166eea9e34ae5551302d4bfa1cdb62ebc479b` | tests/contracts only; no production | 83 focused; Action 15 dual; E1 exact | COMPLETE; paper 910, extended 885 |
| 2F.2 | Full strict regression restart | no commit; baseline `172166e` | output-only | 293 non-medium + 1 medium = 294/294; smoke PASS | COMPLETE; FINAL AUDIT READY |

Commit continuity was verified directly with `git log` and `git show --stat`. `9c584a5` is a Stage 2C evidence bridge before 2D.0; `c5eec0f` adds historical Git-show evidence only and does not alter the A.2 production implementation. Neither is misrepresented as a separate algorithm approval.

Cross-stage resolution:

- Stage 2D left paper-unspecified Ω(B), ordering, and boundary details as engineering decisions; Stage 2F does not retroactively label them PAPER EXPLICIT.
- Stage 2F.2A held the regression, and Stage 2F.1.1 explicitly approved the semantically consumed canonical checker call before the full restart. There is no unresolved conflict.
- No Stage 2G cache, approximation, PPO, RL, top-K, or beam implementation appears in the candidate baseline.
