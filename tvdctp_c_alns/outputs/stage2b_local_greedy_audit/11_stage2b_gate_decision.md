# Stage 2B gate decision

| Gate | Result | Evidence |
| --- | --- | --- |
| Single target route | PASS | Target selector returns one ID; direct trace test |
| Local van scope | PASS | `visited_van_ids == [target]`; single-route helper |
| Local drone scope | PASS | launch trace contains target only |
| Cross-van preserved | PASS | Scoped cross-van move applied and full-feasible |
| No global fallback | PASS | Target-infeasible/other-route-feasible test leaves unassigned |
| Global unchanged | PASS | All-route van trace, explicit-all drone equivalence, full regression |
| Candidate distinction | PASS | Controlled cheaper-B test and real 33-vs-34 comparison |
| Deterministic | PASS | Three identical 30-iteration profiles and Local unit runs |
| Full feasible | PASS | Focused full-checker tests and all ALNS regression cases |
| Candidate count safe | PASS | Local 33 < Global 34 on real fixed case |
| Full pytest | PASS | 82 passed, 5 warnings |
| Scope clean | PASS | Diff limited to Local implementation/helpers/tests/reports |
| Worktree valid | PASS | `git diff --check` passes |

## Final decision

STAGE 2B COMPLETE
