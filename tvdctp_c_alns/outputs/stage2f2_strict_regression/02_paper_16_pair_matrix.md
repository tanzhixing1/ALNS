# Paper 16-Pair Contract Matrix

Fixture: Stage 2D coordinated fixture, 8 customers, removal count 1, NumPy seed 29. Every pair ran twice. Full per-run context, RNG, bundle, violation, and fingerprint evidence is in `stage2f2_pair_runs.json`.

| ID | Pair | Selected | Actually unassigned | Path | Adapter | Bundles | Category | Objective | Feasible | Baseline |
|---:|---|---|---|---|---:|---|---|---:|---|---|
| 0 | Random + Global | 12 | 12 | Ordinary | 0 | n/a | B | 40927.316361140 | no | exact |
| 1 | Random + Local | 12 | 12 | Ordinary | 0 | n/a | B | 40927.316361140 | no | exact |
| 2 | Random + Regret | 12 | 12 | Ordinary | 0 | n/a | A | 926.373751792 | yes | exact |
| 3 | Random + Cascade | 12 | 12 | Ordinary | 1 | `[12]` | A | 927.880274816 | yes | exact |
| 4 | Greedy + Global | 7 | 7 | Ordinary | 0 | n/a | A | 765.252317540 | yes | exact |
| 5 | Greedy + Local | 7 | 7 | Ordinary | 0 | n/a | A | 773.150287337 | yes | exact |
| 6 | Greedy + Regret | 7 | 7 | Ordinary | 0 | n/a | A | 765.252317540 | yes | exact |
| 7 | Greedy + Cascade | 7 | 7 | Ordinary | 1 | `[7]` | A | 791.639335388 | yes | exact |
| 8 | Related + Global | 12 | 12 | Ordinary | 0 | n/a | B | 40927.316361140 | no | exact |
| 9 | Related + Local | 12 | 12 | Ordinary | 0 | n/a | B | 40927.316361140 | no | exact |
| 10 | Related + Regret | 12 | 12 | Ordinary | 0 | n/a | A | 926.373751792 | yes | exact |
| 11 | Related + Cascade | 12 | 12 | Ordinary | 1 | `[12]` | A | 927.880274816 | yes | exact |
| 12 | Cascade + Global | 12 | 12 | Native | 0 | `[12]` | B | 40927.316361140 | no | exact |
| 13 | Cascade + Local | 12 | 12 | Native | 0 | `[12]` | B | 40927.316361140 | no | exact |
| 14 | Cascade + Regret | 12 | 12 | Native | 0 | `[12]` | A | 926.373751792 | yes | exact |
| 15 | Cascade + Cascade | 12 | 12 | Native | 0 | `[12]` | A | 927.880274816 | yes | exact |

- A: 10
- B: 6
- C: 0
- D: 0
- A+B: 16
- Action mapping changed: no
- Both runs identical on all recorded stable fields: yes

Result: **PAPER 16-PAIR CONTRACT PASS**.

