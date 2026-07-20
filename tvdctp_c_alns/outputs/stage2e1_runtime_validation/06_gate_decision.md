# Gate Decision

| Gate | Result | Evidence |
| --- | --- | --- |
| HEAD is Stage 2E.1 commit | PASS | exact HEAD `760e3bc445b04fd2673c81774c90d30422f890df` |
| Worktree initially clean | PASS | initial `git status --short` empty |
| Extended destroy/repair sets identified | PASS | live production registry plus solver source |
| Extended action count = 35 | PASS | production API audit |
| destroy_count x repair_count = 35 | PASS | 7 x 5 = 35 |
| Extended pairs equal full Cartesian product | PASS | set equality |
| Missing extended cross pairs = 0 | PASS | empty difference |
| Extra extended pairs = 0 | PASS | empty difference |
| Paper IDs 0-15 stable | PASS | live paper/extended registry comparison |
| Default main resolves paper_mode | PASS | 5-iteration history |
| Default equals explicit paper | PASS | deterministic fields and byte comparison |
| Paper main run completes | FAIL | 80-iteration command timed out at approximately 901.648 s |
| Paper selected actions all valid | NOT EVALUATED | no formal history persisted; smoke IDs were valid |
| Extended main run completes | NOT RUN | stopped after paper timeout |
| Extended selected actions all valid | NOT RUN | stopped after paper timeout |
| No reroll | PASS (static/smoke) | two independent choices and direct pair lookup; no rerun after timeout |
| No masking | PASS (static/smoke) | no action mask in selection path |
| No pair replacement | PASS (static/smoke) | selected names feed direct registry lookup |
| No silent fallback | PASS (static/smoke) | strict registry/mode path; smoke remained paper_mode |
| Invalid mode fails fast | NOT RUN | stopped after paper timeout |
| Runtime metrics complete | FAIL | formal run produced no result object or persisted history |
| No production changes | PASS | only `outputs/stage2e1_runtime_validation` created |
| No new commit | PASS | HEAD unchanged |

## Decision

- `EXTENDED INDEPENDENT-ROULETTE CONTRACT PASS`
- `DEFAULT PAPER ENTRY CONTRACT PASS`
- `PAPER 80-ITERATION RUNTIME VALIDATION TIMEOUT`
- `STAGE 2E.1 RUNTIME VALIDATION INCOMPLETE`

The timeout is kept separate from registry correctness and solution feasibility. It does not demonstrate a mode defect, but it prevents the requested full runtime-validation PASS.
