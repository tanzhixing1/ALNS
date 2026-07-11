# Scope and diff review

| File | Function/section | Change | Why allowed |
| --- | --- | --- | --- |
| `operators.py` | Regret candidate enumerators | Added complete van and drone concrete-move enumeration | Minimal complete-candidate interface required by Stage 2C |
| `operators.py` | Regret identity/scoring/ranking helpers | Added structural dedup and exact objective-delta ranking | Regret-only correctness helpers |
| `operators.py` | `regret_repair` | Replaced mode-level regret with dynamic true Regret-2 and optional trace | Stage 2C public implementation target |
| `tests/test_stage2c_regret2.py` | 20 tests | Added all required semantic and regression cases | Regret-specific validation |
| `outputs/stage2c_regret2_audit/*` | Reports | Added required evidence | Explicit Stage 2C deliverables |

Forbidden modules/functions changed: NO

- Global/best-mode algorithm: NO
- Local greedy: NO
- Cascade: NO
- Greedy drone: NO
- destroy operators/registry/operator count: NO
- checker/objective/initial solution: NO
- SA/ALNS/adaptive weights: NO
- data/config/evaluation/visualization: NO
- Stage 2A/2B audit artifacts: NO

The new complete enumerators are called only by Regret. Existing `_best_van_move`, `_best_drone_move`, `_all_moves`, Local scope, and Cascade paths remain intact.

Checks: `git diff --check` PASS; no cache, coverage, temporary script, or large intermediate profile is included.
