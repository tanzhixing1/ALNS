# Stage 2F.2 Strict Regression

## Outcome

The 16-pair contract, ordinary isolation, Native attribution, adapter boundary, lifecycle, atomicity, determinism, action registry, frozen-component audit, and representation-gap checks passed. Stage 2F.1 baseline recheck passed 81/81.

Stage 2E.1 grouped regression reproducibly failed two non-medium checker-call-count assertions by +1. The business action sequence, RNG digest, final objective, final fingerprint, and objective-call counts remained at baseline, but the existing suite is not green. Per strict stop policy, the full non-medium run, medium run, and small main smoke were not executed; no production or test baseline was changed.

```text
STAGE 2F.2 REGRESSION BLOCKED
NEW NON-MEDIUM TEST FAILURE
STAGE 2 FINAL AUDIT HELD
STAGE 2G HELD
FULL SUITE PASS NOT CLAIMED
```

## Key numbers

- Git: HEAD `9488139b8920640b47a8a901e32129df0076200f`; tracked/staged/production diff zero.
- Stage 2F.1 recheck: 81 passed in 31.68 s.
- Collection: 292 total; 291 non-medium; 1 medium.
- 16 pairs: A=10, B=6, C=0, D=0.
- Ordinary pairs: 12/12 exact baseline.
- Native pairs: 4/4 baseline on the fixed seed; non-trivial R* fixtures deterministic.
- Group blocker: Stage 2E.1, 52 passed / 2 failed.
- Test commit: none; all new evidence is untracked output-only material.

## Stage boundary

- Stage 2 Final Audit ready: no.
- Stage 2 Final Audit performed: no.
- Stage 2G performed: no.
- C-ALNS paper baseline frozen: not claimed.

