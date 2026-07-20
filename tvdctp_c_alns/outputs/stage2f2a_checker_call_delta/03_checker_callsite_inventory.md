# Checker Call-site Inventory

The AST inventory covers both commits, all production modules, and all tracked tests while excluding historical `outputs`.

- Canonical definition: 1.
- Import bindings: 18 across production/tests.
- Direct calls: 53 across production/tests.
- Production subset: 1 definition, 6 imports, 14 direct calls.
- Added/removed checker call sites between commits: **0**.
- Import aliases affecting this fixture: **0**; production uses the bound name `check_solution_feasible`.

Production boundaries include:

| File/function | Phase |
|---|---|
| `alns_solver.run_c_alns` (2 calls) | initial and final-best validation |
| `objective.objective` | objective/candidate feasibility |
| `initial_solution` (2 calls) | construction candidate and final initial validation |
| `operators._partial_repair_hard_feasible` | partial repair validation |
| `operators._state_is_feasible_and_no_worse` | consolidation boundary |
| `operators.consolidate_drone_sorties` | consolidation boundary |
| `operators._validate_cascade_candidate` | Cascade candidate/final validation |
| `operators.repair_is_complete` | repair completion boundary |
| `evaluation` / `diagnose_calns` | reporting/diagnostic boundaries, not used by this fixture |

The exact extra call uses the pre-existing `_validate_cascade_candidate` call site. Stage 2F.1 did not add or move that helper semantically; it changed whether action 15 reaches it.

The complete matrix is in `03a_checker_callsite_inventory.csv`.

