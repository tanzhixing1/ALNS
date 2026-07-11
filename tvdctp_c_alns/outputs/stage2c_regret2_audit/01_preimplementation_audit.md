# Stage 2C preimplementation audit

Audit completed before Stage 2C source changes.

## Current call path and behavior

1. Public implementation: `operators.py::regret_repair`, beginning at baseline line 1917.
2. Customer loop: copy State, then `while repaired.unassigned`; each round iterates the current `unassigned` list in order.
3. Van candidate: `_all_moves` calls `_best_van_move`, which scans all repair routes/positions but returns only one best van move.
4. Drone candidate: `_all_moves` calls `_best_drone_move`, which explores existing drone paths but returns only one best drone move.
5. Therefore Regret receives only `_best_van_move()` rather than all feasible van positions.
6. It likewise receives only `_best_drone_move()` rather than all concrete launch/recovery strategies.
7. With both modes available, regret is the difference between the best drone and best van after `_all_moves` cost sorting. With one mode, the single move's cost is used as regret.
8. It can omit the second-best van, second-best drone, second position on one route, and second launch/recovery combination.
9. Candidates are not computed only once at repair entry.
10. The outer `while` recomputes all remaining customers after every applied move.
11. Customer ties retain the first current `unassigned` customer because replacement uses strict `>` on regret only. Move ties use stable van-before-drone ordering from `_all_moves`.
12. Zero-candidate customers are skipped; other customers may still be inserted. If every remaining customer has zero candidates, the loop breaks and returns them unassigned. A single candidate uses its cost as regret.
13. Concrete duplicate identity cannot be audited from the compressed two-move output; drone enumeration can reach the same practical move through multiple anchor paths.
14. Global/best-mode and Local share low-level feasibility/cost helpers, but Stage 2B Local has a separate van route-scope helper and scoped drone launch parameter.
15. Safe extension: add Regret-only complete enumerators that reuse existing hard-feasibility checks and `_apply_move`, leaving `_best_*`, `_all_moves`, Local, Global, and Cascade callers unchanged.

## Required-behavior table

| Item | Current behavior | Paper-required behavior | Stage 2C change |
| --- | --- | --- | --- |
| Candidate scope | At most best van + best drone | All concrete feasible moves | Add Regret-only complete van/drone enumeration |
| First/second choice | Best of two mode representatives | Global top two concrete strategies | Unified stable ranking of deduplicated Ω(i) |
| Customer selection | Maximum compressed regret | Maximum true Regret-2 | Structured customer ranking |
| Recalculation | Already after each insertion | After each insertion | Preserve the outer while/recompute behavior |
| Single candidate | Uses move cost as regret | Paper unspecified | Implementation choice: structured priority above multi-candidate customers |
| Tie-break | First unassigned customer on equal regret | Paper unspecified | Stable regret, best delta, original order, customer ID |
| Duplicate handling | Hidden by best-only compression | Engineering requirement | Deduplicate by complete move identity, never by cost |

## Exact-delta finding

The existing `InsertionMove.cost` is a transport/fixed-cost insertion delta used by existing greedy operators. On a partially repaired State it is not guaranteed to equal the complete objective delta because the full objective includes feasibility penalties. Stage 2C will not alter that shared cost or `objective.py`. Regret-only candidates will instead be scored exactly as `objective(apply(copy(state), move)) - objective(copy(state))`, reusing `_apply_move`; this preserves Global/Local semantics while satisfying the Stage 2C objective-equivalence gate.
