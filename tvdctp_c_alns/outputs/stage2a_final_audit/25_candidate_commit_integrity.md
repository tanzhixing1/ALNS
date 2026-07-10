# Candidate Apply/Commit Integrity

- rejected candidate count: 6
- state rollback comparison count: 6
- rollback mismatch count: 0
- current infeasible count: 0
- best infeasible count: 0
- Candidate apply/commit gate: PASS

| Iteration | Before current fingerprint | After rejection fingerprint | Match | Accepted |
| ---: | --- | --- | --- | --- |
| 1 | `c85bfb5184289e2019df51205c4a7d42b61b89abfc9c22960079de195b9f65ac` | `c85bfb5184289e2019df51205c4a7d42b61b89abfc9c22960079de195b9f65ac` | True | False |
| 3 | `38d222c3db263245a540c026382b949324871e5ec9d671868520efc35a8fe2d1` | `38d222c3db263245a540c026382b949324871e5ec9d671868520efc35a8fe2d1` | True | False |
| 4 | `38d222c3db263245a540c026382b949324871e5ec9d671868520efc35a8fe2d1` | `38d222c3db263245a540c026382b949324871e5ec9d671868520efc35a8fe2d1` | True | False |
| 6 | `403560528ca8924114d8b842be41f749436800a92718a9f3a2e157aeab8c12db` | `403560528ca8924114d8b842be41f749436800a92718a9f3a2e157aeab8c12db` | True | False |
| 8 | `7f605bd0b839740984a52c0c28010679e00e5854e16b3805c4562ed9667a5476` | `7f605bd0b839740984a52c0c28010679e00e5854e16b3805c4562ed9667a5476` | True | False |
| 9 | `7f605bd0b839740984a52c0c28010679e00e5854e16b3805c4562ed9667a5476` | `7f605bd0b839740984a52c0c28010679e00e5854e16b3805c4562ed9667a5476` | True | False |

The solver builds candidates from `current.copy()` and only assigns `current = candidate` inside `if accepted`; infeasible candidates cannot reach SA acceptance. Best updates are guarded by `candidate_feasible`. The runtime fingerprints confirm the code-path invariant for all rejected candidates.
