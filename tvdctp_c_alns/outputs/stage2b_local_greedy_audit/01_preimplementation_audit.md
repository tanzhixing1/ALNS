# Stage 2B preimplementation audit

Audit completed before Stage 2B source changes.

## Call paths

- Registered Local repair: `greedy_van_repair` -> `_best_van_move` -> `_repair_van_routes` -> every route and every insertion position -> `_van_insert_hard_feasible` -> `_apply_move`.
- Global/best-mode repair: `best_mode_repair` -> `_all_moves` -> `_best_van_move` plus `_best_drone_move` -> `_apply_move`.
- Drone candidate generation: `_best_drone_move` -> `_best_drone_move_for_customers`; both the outer anchor loops and the inner generator traverse all launch routes. The inner generator also traverses every recovery route.
- Greedy-drone fallback: `greedy_drone_repair` -> `greedy_van_repair` when customers remain.

## Findings

1. `greedy_van_repair` is the public function currently registered as Local.
2. It calls the same global van candidate helper used by best-mode/Global behavior.
3. `_best_van_move` generates van candidates and `_repair_van_routes` supplies all present routes plus eligible unused vans.
4. `_best_drone_move` and `_best_drone_move_for_customers` generate drone candidates.
5. `_best_van_move`, `_best_drone_move`, and `_best_drone_move_for_customers` all contain all-route traversal.
6. There is no existing Local target-route selector.
7. Local copies the state and calls `rng.shuffle(repaired.unassigned)`; this order must be preserved.
8. Local and Global share the van helper, while the current Local does not call the drone helper at all.
9. Existing cost-delta functions, hard-feasibility functions, `_apply_move`, and stable cost sorting are safe to reuse.
10. Stage 2B needs Local-only route selection and explicit launch-route scope for drone generation. Global defaults must remain unrestricted.

## Required-behavior table

| Item | Current behavior | Paper-required behavior | Planned change |
| --- | --- | --- | --- |
| Target route selection | None | Exactly one deterministic route | Add a Local-only selector using prior assignment, explicit warehouse mapping, then stable first-route fallback |
| Van candidates | All repair routes | Target route only | Add a single-route van generator reusing current feasibility and cost delta |
| Drone candidates | None in Local; all launch routes in shared helper | Target launch route only | Add an optional launch scope with unrestricted legal recovery routes |
| Cross-van recovery | Enumerated | Preserve existing legal cross-van recovery | Restrict launch only; do not restrict recovery |
| Failure behavior | Van-only attempt; otherwise unassigned | Fail locally without scanning other routes | Keep customer unassigned and continue |

## Scope risk noted before implementation

`greedy_drone_repair` currently delegates its remaining customers to `greedy_van_repair`. Directly changing that nested call's meaning would alter a prohibited operator. The Local entry point therefore needs a compatibility branch when its immediate caller is `greedy_drone_repair`, preserving the pre-Stage-2B global van-only fallback without editing the greedy-drone function itself.
