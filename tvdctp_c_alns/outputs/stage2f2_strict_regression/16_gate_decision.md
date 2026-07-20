# Gate Decision

| Gate | Result | Evidence |
|---|---|---|
| Baseline HEAD correct | PASS | `9488139b…` |
| Tracked/staged initially clean | PASS | Git gate |
| Stage 2F.1 focused recheck | PASS | 81/81 |
| Paper 16 pairs classified | PASS | A=10 B=6 C=0 D=0 |
| Ordinary 12 unchanged | PASS | 12/12 hard baseline |
| Ordinary RNG/adapter unchanged | PASS | exact digests/calls |
| Native four changes explained | PASS | no matrix change; non-trivial traces valid |
| Native R*/bundles/Path B | PASS | exact membership and partitions |
| Native bypasses adapter | PASS | 0 calls |
| Context lifecycle / failure atomicity | PASS | focused and pair evidence |
| Determinism / Native RNG | PASS | all double-runs equal |
| paper_mode / 16 IDs / extended registry | PASS | registry evidence |
| Stage 2D grouped | PASS | 18 + 40 |
| Stage 2E grouped | FAIL | Stage 2E.1 has 2 failures |
| Stage 2F grouped | PASS | 81 focused + pair probe |
| All non-medium | FAIL | not runnable to PASS after grouped failure |
| Medium status honest | PASS | one node identified, not run |
| Small main smoke | FAIL | not run after stop condition |
| Frozen components unchanged | PASS | static diff |
| Known gaps preserved | PASS | predicate/exclusion evidence |
| Production diff zero | PASS | tracked diff empty |
| No performance work | PASS | scope review |
| Final Audit not performed | PASS | held |
| Stage 2G not performed | PASS | held |
| Final Audit readiness | FAIL | held |

Failure fixture and minimal reproduction:

```text
C:\Users\19088\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_stage2e1_operator_modes.py
```

Observed twice: paper checker calls `910 != 909`; extended checker calls `885 != 884`. No production or test expectation was edited.

```text
STAGE 2F.2 REGRESSION BLOCKED
NEW NON-MEDIUM TEST FAILURE
STAGE 2 FINAL AUDIT HELD
STAGE 2G HELD
FULL SUITE PASS NOT CLAIMED
NO_COMMIT_REQUIRED
```

