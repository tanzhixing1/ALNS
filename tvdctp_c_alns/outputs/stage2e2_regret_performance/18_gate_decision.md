# Gate Decision

| Gate | Result | Evidence |
|---|---|---|
| Baseline correct | PASS | HEAD and Stage 2E.1-P artifacts |
| Duplicate work quantified | PASS | reports 01-04 |
| Safe optimization identified | PASS | exact invocation-local prototype |
| Cache repair-local / no global cache | PASS (prototype) | temporary scope tests |
| Cache key complete | PASS (prototype) | report 06 |
| Candidate universe/order/identities unchanged | PASS (prototype) | focused semantic tests |
| Objective/checker results unchanged | PASS (prototype) | exact fingerprint/results |
| First/second best, regret, selected customer/move unchanged | PASS (prototype) | semantic trace |
| Final fingerprint and RNG unchanged | PASS (prototype) | report 07/14 |
| Other repairs and Stage 2E contracts unchanged | PASS (final baseline) | empty production diff + regressions |
| No truncation/approximation | PASS | design and diff review |
| Focused speedup achieved | **FAIL** | `6.775417849251609%` < `30%`; calls `3.468354430379747%` < `40%` |
| 20-iteration speedup | NOT RUN | focused prerequisite failed |
| 40-iteration speedup | NOT RUN | focused/20 prerequisites failed |
| 80 exact regression and speedup | NOT RUN | prerequisites failed |
| Memory acceptable | NOT ESTABLISHED | baseline peak unavailable |
| Tests passed relative to baseline | PASS | 274 passed, 1 known medium deselected |
| Scope clean | PASS | rejected implementation reverted |
| Git diff check | PASS | no tracked diff errors |

## Final decision

```text
STAGE 2E.2 PERFORMANCE TARGET NOT MET
STAGE 2F HELD
```

No commit is permitted or created.
