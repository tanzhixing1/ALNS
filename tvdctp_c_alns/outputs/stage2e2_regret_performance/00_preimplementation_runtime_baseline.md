# Pre-implementation Runtime Baseline

Baseline HEAD: `760e3bc445b04fd2673c81774c90d30422f890df`

Source artifacts are the unchanged Stage 2E.1-P outputs under `outputs/stage2e1_runtime_diagnosis/`.

## Graded runtime

| Iterations | Solver seconds | ALNS loop seconds | Regret calls | Regret raw candidates | Regret hard-feasible candidates | Objective calls | Checker calls | State.copy calls | deepcopy object count |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 134.957018799847 | 131.3144578000065 | 2 | 37,618 | 19,516 | 19,637 | 21,457 | 21,465 | 150,255 |
| 20 | 206.5394520999398 | 203.10319180018269 | 5 | 69,673 | 37,941 | 38,252 | 40,100 | 40,112 | 280,784 |
| 40 | 596.0500053002033 | 592.6118789000902 | 11 | 178,994 | 85,751 | 86,425 | 88,312 | 88,345 | 618,415 |

The 40-run maximum repair call was iteration 35, action 14 (`cascade_aware_removal + regret_repair`): `230.98507660022005 s`, `58,588` raw candidates, `26,652` hard-feasible candidates, `58,098` persisted unique-drone-candidate count, `26,788` objective calls, and `26,794` checker calls. The persisted trace does not contain the complete whole-candidate identity sequence, so it is not relabelled as a whole-candidate unique count.

## Regret calls in the 40-run

| Iteration | Action | Repair seconds | Raw | Hard feasible | Persisted unique drone | Objective calls | Checker calls |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 6 | 9.576209500199184 | 4,900 | 1,773 | 4,806 | 1,785 | 1,787 |
| 10 | 2 | 94.88496790011413 | 32,718 | 17,743 | 32,514 | 17,784 | 17,790 |
| 11 | 10 | 22.836570099927485 | 7,259 | 3,994 | 7,166 | 4,014 | 4,018 |
| 16 | 2 | 36.42156339995563 | 13,662 | 7,652 | 13,398 | 7,697 | 7,701 |
| 17 | 2 | 31.587633799994364 | 11,134 | 6,779 | 11,052 | 6,809 | 6,812 |
| 28 | 10 | 14.688905499875546 | 3,796 | 2,207 | 3,740 | 2,218 | 2,219 |
| 34 | 2 | 30.303336100187153 | 8,246 | 4,810 | 8,068 | 4,844 | 4,849 |
| 35 | 14 | 230.98507660022005 | 58,588 | 26,652 | 58,098 | 26,788 | 26,794 |
| 36 | 2 | 34.01593369990587 | 14,376 | 5,237 | 14,253 | 5,257 | 5,259 |
| 37 | 14 | 30.49974190001376 | 13,641 | 4,002 | 13,466 | 4,026 | 4,028 |
| 40 | 14 | 37.553901500068605 | 10,674 | 4,902 | 10,444 | 4,942 | 4,943 |

## True 80-iteration main

- External wall: `2776.331017700 s`
- Solver runtime: `2075.4630972000305 s`
- Initial objective: `1484.4917238190928`
- Final best objective: `1070.9374426979527`
- Feasible: `True`
- Violations: none
- Registry fingerprint: `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`
- `summary.txt` SHA-256: `6F0EA9C59BB46885238D62ACE6B91CC80087B2F535F0F0615EC596028D79B6FF`
- `route_plan_detail.csv` SHA-256: `99046F0004236C6D48B7FD2F639405DF2A4B53766AE08420C4F45BF64310F465`

The old run did not persist `_state_business_fingerprint`; the two artifact hashes above are recorded as artifact-integrity fingerprints and are not falsely presented as the production business fingerprint. Strict post-implementation comparison will use the full history trajectory and business route/state fields.

The exact 80-row action/destroy/repair/acceptance/current/best trace is copied without numeric rounding into `00a_preimplementation_iteration_trace.csv`.
