# Trace Instrumentation Validation

The untracked probe replaces every production-bound checker reference with one wrapper that calls the original checker exactly once. It also observes the existing solver RNG object without drawing from it and observes the existing objective counter without invoking objective. No exception, ordering, acceptance, or candidate-selection branch is replaced.

Each version/mode was instrumented twice in a separate Python process.

| Mode/version | Trace/profile count | Objective calls | RNG digest | Final objective/fingerprint | Deterministic |
|---|---:|---:|---|---|---|
| baseline paper | 909/909 | 653 | frozen match | frozen match | yes |
| current paper | 910/910 | 653 | frozen match | frozen match | yes |
| baseline extended | 884/884 | 608 | frozen match | frozen match | yes |
| current extended | 885/885 | 608 | frozen match | frozen match | yes |

All action IDs/names, accepted flags, candidate-feasible flags, RNG digests, final objectives, and final State fingerprints match the uninstrumented frozen harness. RNG fingerprints before/after every checker call are equal.

The canonical checker itself refreshes timing and sortie-position fields on some input working copies; the wrapper merely records that original behavior. In particular, the extra action-15 snapshot candidate's fingerprint changes across the original checker while routes and unassigned membership remain the candidate's own disposable data. This mutation is not caused by instrumentation and does not reach persistent current/best State.

Result: **behavior-neutral instrumentation PASS**.

