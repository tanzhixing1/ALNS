# Context Lifecycle and Atomicity

## Lifecycle

- Persistent current/best: no active removal context.
- Destroyed candidate: carries exactly one temporary context.
- Repair boundary: detaches and consumes/clears context.
- Repair return, accepted current, and global best: context-free.

Evidence: 28 Stage 2E-A.1 tests, 33 Stage 2E-A.2 tests, the 32 pair runs, both Action 15 traces, and the solver persistent-state tests.

## Native success and Path B

Every Native matrix run and non-trivial fixture satisfied `actual newly_unassigned == R*`. The caller/source State signature stayed unchanged. The injected mismatch test raised `ATOMIC CO-REMOVAL CONTRACT VIOLATION`, discarded the isolated working copy, left caller business State/metadata unchanged, attached no context, and used no fallback.

## Cascade repair atomicity

- Empty Ω(B) and later-bundle failure tests return the original destroyed business fingerprint.
- Earlier bundle work is discarded on a later failure.
- No partial candidate or half-completed structural context is retained.
- No Global/Local/Regret/finalize/consolidation fallback is called.

## Action 15 failure

Each mode produces exactly one snapshot candidate. The canonical checker rejects it; objective scoring stays zero; repair returns the destroyed business State with failure diagnostics; RNG is unchanged and context is cleared. Final solver best State and fingerprint remain frozen.

```text
CONTEXT LIFECYCLE PASS
ATOMIC FAILURE CONTRACT PASS
```
