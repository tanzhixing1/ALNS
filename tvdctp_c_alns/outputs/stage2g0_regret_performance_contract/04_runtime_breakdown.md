# Runtime Breakdown — Current Frozen Baseline

- Clean heavy Regret wall: **120.612752 s**.
- Candidate generation: 16.431495 s inclusive; hard prefilter
  10.254218 s is a subset. Drone enumeration is
  16.422072 s versus van
  0.009423 s.
- Exact scoring: 106.933091 s inclusive.
- `State.copy`: 17,786 calls,
  23.877473 s (19.80% of clean wall).
- Candidate application: 0.178422 s.
- `compute_timing`: clean 35,496 calls / 48
  hits; observer 53.273776 s inclusive,
  45.258740 s exclusive.
- Objective: clean 17,784 calls; observer
  81.768283 s inclusive,
  11.461532 s exclusive.
- Checker: clean 17,792 calls / 80
  hits; observer 40.688321 s inclusive,
  12.018855 s exclusive.
- Move identity + State signature traversal: 13.392032 s nested.
- Sorting/tie construction plus customer-level residual: about
  0.313860 s. Selected commit: only
  0.00005180 s.
- Per-customer evaluation P50/P90/P95/P99:
  4.757283 /
  7.119995 /
  7.425704 /
  8.829042 s.
- Clean absolute peak working set/private bytes:
  1,451,347,968 / 1,981,620,224. This is a
  process-level peak including Python/runtime and captured fixture state, not an
  incremental candidate-only allocation.

Inclusive values overlap by design and must not be summed. The dominant roots
are exhaustive drone enumeration, full candidate materialization, and repeated
timing/checker traversal during exact scoring.
