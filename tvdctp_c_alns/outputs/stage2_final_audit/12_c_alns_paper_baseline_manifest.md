# C-ALNS Paper Baseline Manifest

- Git commit: `172166eea9e34ae5551302d4bfa1cdb62ebc479b`
- Python: 3.12.13
- pytest: 9.1.1
- default mode: `paper_mode`
- paper registry: 16 actions, IDs 0–15, fingerprint `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`
- extended registry: explicit-only 35 actions, fingerprint `588c3c20cc1b34c66bb90f4e6e3296af5397f1ad4ba671b07d59f1f15a446514`
- Stage 2F.2: 293 non-medium + 1 medium = 294/294 passed; 5 existing warnings; no failures
- final targeted gate: 31 passed in 18.16 s
- main smoke: default/explicit PASS, best `811.9529412450966`, feasible, zero violations, identical 10-row histories
- known gaps: recorded in `11_known_gap_register.md`

## Core production Git blobs

| Path | Blob |
|---|---|
| `config.py` | `1bc29489f2019b8445f472baaac442ab8b4d7ba9` |
| `state.py` | `40bad0e83fcd08dfc4243837abb2482ed2052822` |
| `initial_solution.py` | `d1b7278419ff4a12c010fac29dcac0576d2a5abd` |
| `operators.py` | `612c18a701e8c1e8bb8948c139f4f552bb3a9f30` |
| `removal_structural_context.py` | `93ff9cb381eac14e6e77afbbf403ac4faefa0372` |
| `ordinary_cascade_adapter.py` | `aa26ec5875dc6ec36b6cb939ce48515cdd3f3850` |
| `objective.py` | `bd94b9bc76d11a1ee7b5234d2625f516bacbb00a` |
| `feasibility.py` | `a9494e7874cc650e9af5a90f2760333a62d0e49d` |
| `alns_solver.py` | `14cb1b2a6c010dd84b2230a80bd21b6549611b82` |
| `main.py` | `19d591b369fdb5e3911e6d57d21ec29f45b50617` |
| `operator_modes.py` | `747b4db093c3cc15868bdb41eba2f2e9a6354298` |

## Core test Git blobs

| Path | Blob |
|---|---|
| `tests/test_regression_rules.py` | `aaff6bce77f79a587c2ac8cdfd57e939d8fa1db9` |
| `tests/test_stage2a_drone_feasibility.py` | `c9be54802161af762cd44bc578bb572e6b0db197` |
| `tests/test_stage2b_local_greedy.py` | `2cd8dc877cd8c57c5dbdda7f49168ffc271e66f4` |
| `tests/test_stage2c_regret2.py` | `622476e0a17543d919f126ea85dc21f8b8bbbbf3` |
| `tests/test_stage2d0_cascade_contract.py` | `5ed35cfabb03880d7b6db3c96399a946cfe1dddc` |
| `tests/test_stage2d1_cascade_repair.py` | `a03a6d11736fc7537c44cf19f25b471a89b976da` |
| `tests/test_stage2d_multidrone_coverage.py` | `ef62364c097b133edc8526aee973628bd059c231` |
| `tests/test_stage2ea1_structural_context.py` | `2f36c7a3e01c58530f37de08a005463d1037f0d8` |
| `tests/test_stage2ea2_ordinary_cascade_adapter.py` | `3b51edc0cc71ad66f5e5fc032e11ff65fdced06b` |
| `tests/test_stage2e1_operator_modes.py` | `6f175c07dff5b234ba6cd9b2592f2da23ccd6941` |
| `tests/test_stage2f1_native_cascade_removal.py` | `4f8e0b9029c8303b6ed869a114563c74d2eacd39` |

All hashes were resolved as Git objects at `HEAD`, not from timestamps. A future maintainer may manually create a tag such as `c-alns-paper-baseline-v1`; this audit did **not** create a tag.
