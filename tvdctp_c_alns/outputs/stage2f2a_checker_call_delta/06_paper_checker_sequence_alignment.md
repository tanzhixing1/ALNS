# Paper Checker Sequence Alignment

- Baseline calls: 909.
- Current calls: 910.
- First divergence: baseline call 484 versus current calls 484–485.
- Exact extra current call: **484**.
- Iteration/action: iteration 7, action 15 (`cascade_aware_removal` + `cascade_repair`).
- Direct caller: `operators.py::_validate_cascade_candidate`, current line 3670.
- Stack: `run_c_alns > cascade_repair > _enumerate_bundle_reconstruction_strategies > _validate_cascade_candidate`.
- Phase: Cascade repair snapshot-candidate validation.

Strict State-aware alignment is not a pure insertion. It is a one-to-two replacement block:

1. Baseline action-15 final candidate is checked by `objective` at call 484.
2. Current first checks a distinct snapshot working copy at call 484.
3. Current then checks a different action-15 returned candidate through `objective` at call 485.

After that block, calls 485–909 baseline align exactly with calls 486–910 current. There are no later insertions, deletions, reorderings, or replacements.

Baseline action 15 aborts Cascade repair before enumeration because the old Native contract reports overlapping/invalid bundle memberships (`checker_call_count=0`). Current Native output is a valid single bundle of size 3; Cascade generates exactly one raw snapshot candidate, calls the canonical checker once, rejects it as infeasible, obtains zero feasible strategies, and returns a failed repair result.

CSV evidence: `06a_paper_checker_trace_baseline.csv`, `06b_paper_checker_trace_current.csv`.

