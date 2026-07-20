# Frozen Component Review

The worktree blob IDs match baseline `172166ee...` exactly:

| File | Blob | Match |
|---|---|---|
| `objective.py` | `bd94b9bc76d11a1ee7b5234d2625f516bacbb00a` | yes |
| `feasibility.py` | `a9494e7874cc650e9af5a90f2760333a62d0e49d` | yes |
| `state.py` | `40bad0e83fcd08dfc4243837abb2482ed2052822` | yes |
| `operators.py` | `612c18a701e8c1e8bb8948c139f4f552bb3a9f30` | yes |
| `alns_solver.py` | `14cb1b2a6c010dd84b2230a80bd21b6549611b82` | yes |
| `operator_modes.py` | `747b4db093c3cc15868bdb41eba2f2e9a6354298` | yes |

This freezes objective, canonical checker, timing propagation, State business fields/copy, Global/Local/True Regret-2/Cascade repair, `_validate_cascade_candidate`, SA acceptance, adaptive weights, and both registries relative to the approved baseline.

History separation:

- Stage 2F.1 (`760e3bc..9488139`): production change only in Native `operators.py`, with its Stage 2D.0/F1 tests.
- Stage 2F.1.1 (`9488139..172166e`): tests/contracts only (`test_stage2e1_operator_modes.py`, `test_stage2f1_native_cascade_removal.py`); no production change.
- This restart: output-only reports, JSON/CSV probes and smoke artifacts; no tracked production/test change.

No objective/checker/State/repair/SA/weight/registry behavior changed in this round.
