# Extended Checker Sequence Alignment

- Baseline calls: 884.
- Current calls: 885.
- First divergence: baseline call 322 versus current calls 322–323.
- Exact extra current call: **322**.
- Iteration/action: iteration 8, action 15 (`cascade_aware_removal` + `cascade_repair`).
- Direct caller: `operators.py::_validate_cascade_candidate`, current line 3670.
- Stack: `run_c_alns > cascade_repair > _enumerate_bundle_reconstruction_strategies > _validate_cascade_candidate`.
- Phase: Cascade repair snapshot-candidate validation.

As in paper mode, State-aware alignment is a one-to-two replacement block, not a pure insertion. The current extra snapshot validation is followed by a different action-15 returned candidate check through `objective`; every call after this block realigns exactly.

Baseline action 15 aborts on the old overlapping/invalid Native bundle contract with no Cascade checker call. Current produces one valid bundle of size 5 and exactly one raw snapshot candidate. The checker rejects that candidate, yielding zero feasible strategies and an empty-strategy failure. No other extended-only action contributes to the delta.

CSV evidence: `07a_extended_checker_trace_baseline.csv`, `07b_extended_checker_trace_current.csv`.

