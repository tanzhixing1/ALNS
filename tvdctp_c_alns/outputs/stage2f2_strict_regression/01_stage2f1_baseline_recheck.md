# Stage 2F.1 Baseline Recheck

The recheck included all 68 Stage 2D.0, Stage 2D.1, and Stage 2F.1 core cases plus 13 selected lifecycle, isolation, action-15, and frozen-pair cases used by the Stage 2F.1 evidence boundary.

```text
C:\Users\19088\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_stage2d0_cascade_contract.py tests/test_stage2d1_cascade_repair.py tests/test_stage2f1_native_cascade_removal.py tests/test_stage2ea1_structural_context.py::test_public_repair_lifecycle_consumes_context tests/test_stage2ea1_structural_context.py::test_nested_registered_repair_and_failure_paths_do_not_leak_context tests/test_stage2ea1_structural_context.py::test_solver_persistent_states_are_context_free tests/test_stage2ea1_structural_context.py::test_objective_checker_and_violations_are_context_isolated tests/test_stage2ea1_structural_context.py::test_existing_13_pairs_are_exactly_unchanged tests/test_stage2ea1_structural_context.py::test_cascade_plus_cascade_candidate_sequence_and_contract_are_exact tests/test_stage2ea2_ordinary_cascade_adapter.py::test_native_cascade_bypasses_adapter_and_remains_exact tests/test_stage2ea2_ordinary_cascade_adapter.py::test_adapter_is_lazy_only_for_the_three_new_pairs tests/test_stage2ea2_ordinary_cascade_adapter.py::test_existing_unrelated_repairs_have_identical_work_counts tests/test_stage2e1_operator_modes.py::test_native_cascade_pair_has_frozen_action_fifteen
```

- Collected: 81
- Passed: 81
- Failed: 0
- Runtime: 31.68 s (pytest), 35.2 s wall

Result: **PASS**.

