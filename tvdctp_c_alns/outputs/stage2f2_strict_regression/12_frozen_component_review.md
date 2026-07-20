# Frozen Component Review

Static diff from Stage 2F.0 baseline `760e3bc…` to Stage 2F.1 commit `9488139…` shows production changes only in `operators.py`, limited to Native dependency graph, ordered closure, weak-component partition, Native snapshots/order, and Path B membership validation.

No diff exists in:

- `objective.py`;
- `feasibility.py` / `compute_timing` / canonical checker;
- `state.py` / State fields / signature / copy;
- `initial_solution.py`;
- `alns_solver.py` / SA / weights;
- `operator_modes.py`;
- `config.py` / default mode;
- `main.py`;
- `removal_structural_context.py`;
- `ordinary_cascade_adapter.py`.

Within `operators.py`, ordinary destroys, Global/Local/Regret repairs, Cascade repair Ω(B), candidate generation/scoring, objective/checker implementations, and fallback policy have no diff.

Current tracked and staged diffs remain empty.

