# Stage 2F.2A Canonical Checker Call Delta Root-Cause Audit

## Outcome

The +1 is deterministic and comes from one shared production call site in action 15. Stage 2F.1 makes the Native removal contract valid enough for Cascade repair to enumerate one snapshot candidate; the pre-existing `_validate_cascade_candidate` checker call rejects it. Baseline aborts earlier on overlapping/invalid bundle memberships and never reaches that boundary.

Paper: iteration 7, current call 484. Extended: iteration 8, current call 322. Each mode selects action 15 exactly once, so each gains exactly one checker call.

This is not test accounting and not a redundant duplicate. Under the contract's strict State-aware taxonomy, the sequence changes from one action-15 final-candidate check to a two-call block (snapshot validation plus a different returned-candidate check), then fully realigns. The extra result is consumed and the action-15 candidate State differs; therefore it is classified D rather than an approved diagnostic-only delta.

```text
STAGE 2F.1 SEMANTIC CONTROL-FLOW REGRESSION CONFIRMED
STAGE 2F.1.1 CORRECTION REQUIRED
STAGE 2F.2 HELD
STAGE 2G HELD
NO_COMMIT_REQUIRED
```

No production, tracked test, expectation, checker, objective, State, RNG, registry, or Stage 2F.1 implementation file was changed.

