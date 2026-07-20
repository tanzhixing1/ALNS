# Failing Test Inventory

## Exact nodes

1. `tests/test_stage2e1_operator_modes.py::test_paper_search_work_matches_preimplementation_baseline`
2. `tests/test_stage2e1_operator_modes.py::test_explicit_extended_run_matches_preimplementation_baseline`

Both use the module-scoped `baseline_runs` fixture, which invokes `_baseline_run` once for `OperatorMode.PAPER` and once for `OperatorMode.EXTENDED`.

## Fixture and entry

- Data/build seed: `seed=42`.
- ALNS RNG seed: `config.alns.random_seed = 29`.
- Size: 10 customers/orders, 2 transshipments, 1 container.
- Iterations: 12; early stopping disabled; full candidate diagnostics enabled.
- Production entry: `alns_solver.run_c_alns(data, config)`.
- Counting location: `feasibility.check_solution_feasible`, which increments `check_solution_feasible_calls` at line 1107. `run_c_alns` snapshots the profile before returning.
- The failing assertions only read the returned profile; they do not invoke the checker.

## Historical expected source

- Paper: `BASELINE_P_CHECKER_CALLS = 909` at test line 93; asserted at line 424.
- Extended: `BASELINE_E_CHECKER_CALLS = 884` at test line 129; asserted at line 440.
- These constants and the complete fixture were already present at baseline commit `760e3bc...`.

The adjacent business assertions cover action sequence, RNG digest, objective value/count, and final State fingerprint. They continue to match.

