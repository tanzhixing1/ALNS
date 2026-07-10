# Scope and diff review

| File | Function/section | Change | Why allowed in Stage 2B |
| --- | --- | --- | --- |
| `operators.py` | `_local_target_van` | Added deterministic one-route selection | Local-only helper required by the stage |
| `operators.py` | `_best_van_move_on_route` | Added exact single-route van enumeration | Local-only candidate helper |
| `operators.py` | `_best_drone_move_for_customers`, `_best_drone_move` | Added optional launch scope and optional diagnostic trace; default remains unrestricted | Necessary scoped helper parameters; Global defaults unchanged |
| `operators.py` | `greedy_van_repair` | Replaced all-route van-only behavior with target-scoped van+drone selection; added callback trace | The Stage 2B implementation target |
| `tests/test_stage2b_local_greedy.py` | 10 tests | Added semantic, deterministic, feasibility, candidate-count, and Global-regression tests | Local-specific tests/instrumentation validation |
| `outputs/stage2b_local_greedy_audit/*` | Audit reports | Added required Stage 2B evidence | Explicitly required deliverables |

Confirmed unchanged:

- Global/best-mode repair body and `_all_moves`;
- Regret and Cascade;
- Greedy-drone function body;
- destroy operators and registry;
- feasibility/checker and objective;
- initial solution;
- SA, ALNS loop, and adaptive weights;
- data generation and configuration defaults;
- evaluation and route visualization;
- all Stage 2A audit files.

Git checks before commit:

- `git diff --check`: PASS (only a Git line-ending notice, no whitespace error)
- tracked source/test/report changes are limited to the rows above
- cache/coverage/runtime artifacts are not included
