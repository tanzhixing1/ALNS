# Paper Baseline Component Matrix

“Frozen” means stable under the approved Stage 2 engineering contract at baseline `172166ee`; it does not turn paper-unspecified implementation details into paper requirements.

| Component | Paper/contract basis | Current implementation | Classification | Principal tests/evidence | Frozen |
|---|---|---|---|---|---|
| Initial solution | Feasible TVDCTP-T construction required; exact heuristic not uniquely specified | multi-container drayage, feasible van insertion, mandatory-drone handling, final canonical check | PAPER PARTIAL + APPROVED ENGINEERING DECISION | regression rules; Stage 2A audit; F2 full suite | YES |
| Random removal | random customer removal | sorted served domain, configured count, one choice without replacement, context capture | PAPER PARTIAL + APPROVED ENGINEERING DECISION | EA1/F2 pair evidence | YES |
| Greedy removal | cost-oriented destroy | objective-delta trials, stable deterministic ranking, context capture | PAPER PARTIAL + APPROVED ENGINEERING DECISION | EA1 strict equivalence | YES |
| Related removal | related-customer destroy | frozen relatedness/order and one seed RNG path, context capture | PAPER PARTIAL + APPROVED ENGINEERING DECISION | EA1 strict equivalence | YES |
| Cascade-aware removal | recursive dependency closure and simultaneous R* removal | customer graph, two approved predicates, ordered fixed point, weak components, Path B | PAPER EXPLICIT for closure/R*; PAPER PARTIAL for dependency; engineering details otherwise | F0/F1/F2 | YES, with gaps |
| Global repair | choose best hard-feasible concrete insertion | full van/drone candidate scope and objective comparison | PAPER PARTIAL + APPROVED ENGINEERING DECISION | Stage 2B/2C regressions | YES |
| Local repair | local reconstruction | one target route, target launch scope, legal cross-van recovery, no global fallback | PAPER PARTIAL + APPROVED ENGINEERING DECISION | Stage 2B + targeted node | YES |
| True Regret-2 | Regret(i)=f2-f1 | all unique concrete hard-feasible moves, exact objective deltas, deterministic ties | PAPER EXPLICIT/PARTIAL + APPROVED ENGINEERING DECISION | Stage 2C + targeted node | YES semantically |
| Cascade repair | bundle joint reconstruction and full objective selection | bundle-scoped Ω(B), snapshot/van-block/whole-sortie strategies, canonical validation, atomic failure | PAPER PARTIAL + APPROVED ENGINEERING DECISION | D0/D1/EA2/F2 | YES |
| `paper_mode` | four paper destroys × four paper repairs | strict fixed catalog and fail-fast construction | APPROVED ENGINEERING DECISION grounded in paper catalog | E1 54/54; targeted | YES |
| `extended_mode` | not paper baseline | explicit 7×5 approved catalog, 35 actions | EXTENDED-MODE ONLY | E1/F2 | YES outside paper baseline |
| IDs 0–15 | paper does not assign code IDs | contiguous immutable Cartesian identities | APPROVED ENGINEERING DECISION | E1 exact matrix/fingerprint | YES |
| Ordinary adapter | paper does not specify code adapter | lazy only for Random/Greedy/Related + Cascade; actual-R context | APPROVED ENGINEERING DECISION | EA2/F2 | YES |
| Native adapter bypass | architectural boundary | Native supplies native bundles and makes zero ordinary-adapter calls | APPROVED ENGINEERING DECISION | F1/F2 | YES |
| Objective | cost function plus infeasibility handling | transport/fixed costs + hard-infeasible penalty; waiting reported, not optimized | PAPER PARTIAL + APPROVED ENGINEERING DECISION | Stage 2A/full regression | YES |
| Canonical checker | hard feasibility boundary | production `check_solution_feasible`, used by objective and final gates | APPROVED ENGINEERING DECISION implementing model constraints | A/D/E/F tests | YES |
| `compute_timing` | synchronization/time-window constraints | authoritative timing propagation used by checker | PAPER PARTIAL + APPROVED ENGINEERING DECISION | Stage 2A differential/full regression | YES |
| State business fields | solution representation | routes, carriers, assignments, service modes, unassigned, timing | APPROVED ENGINEERING DECISION | State fingerprints/F2 blobs | YES |
| `State.copy` | not specified | isolated mutable business data; immutable context sharing only | APPROVED ENGINEERING DECISION | D0/EA1/F2 | YES |
| Removal context | not paper object | ephemeral repair-agnostic structure; never persists in current/best | APPROVED ENGINEERING DECISION | EA1/F2 lifecycle | YES |
| SA acceptance | SA stated in C-ALNS | strict improvement or exp(-delta/T) draw | PAPER EXPLICIT/PARTIAL + APPROVED ENGINEERING DECISION | solver/full regression | YES |
| Adaptive weights | adaptive operator selection | independent destroy/repair roulette and segment reaction update | PAPER PARTIAL + APPROVED ENGINEERING DECISION | E1 selection regression | YES |
| Iteration/current/best | C-ALNS loop | evaluate feasible candidate, SA current update, strict global-best update | PAPER PARTIAL + APPROVED ENGINEERING DECISION | A/E/F | YES |
| Termination | finite C-ALNS run | max iterations plus configurable no-improvement early stop | APPROVED ENGINEERING DECISION | solver tests/smoke | YES |
| RNG/determinism | stochastic heuristic; exact API unspecified | one solver-owned NumPy Generator passed through operators; frozen call order per contracts | PAPER UNSPECIFIED + APPROVED ENGINEERING DECISION | deterministic runs and F2 16×2 | YES |

Known conservative Cascade representation gaps remain deliberately outside the implemented customer graph; see `11_known_gap_register.md`.
