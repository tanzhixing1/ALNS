# Stage 2B Gate Decision

## READY FOR STAGE 2B

| Gate | Result | Evidence | Blocking reason |
| --- | --- | --- | --- |
| Config reproducible | PASS | 10/11; identical config fingerprints | — |
| Instance reproducible | PASS | 10/11; `b76654c6fcdedd62f3c6c56a916035962b89908e49bc02320c782c0b59d55dfc` | — |
| Run reproducible | PASS | 10/11; 3 deterministic runs | — |
| Initial objective explained | PASS | 09; high_floor_ratio 0.35 vs 0.15 and different instance fingerprints | — |
| Unknown classified | PASS | 13/14; four Timing / synchronization records | — |
| No checker false-positive | PASS | Stage2A tests + code path + late-service values exceed latest=360 | — |
| Local/full feasibility relation understood | PASS | 13/14/18; insertion-local vs final whole-state full check | — |
| No candidate apply/commit bug | PASS | 25; all rejection rollback fingerprints match | — |
| Full pytest | PASS | 20_pytest_result.txt | — |
| Clean tracked worktree | PASS | tracked status clean; audit directory intentionally untracked | — |
| Visual consistency | PASS | 24/26; fingerprints captured at evaluation.py entry points | — |
| Best State full feasible | PASS | checker violations=[] | — |

Failed gates:
- none
