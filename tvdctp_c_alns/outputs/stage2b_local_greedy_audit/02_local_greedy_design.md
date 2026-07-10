# Local greedy design

## Main flow

For each customer in the existing shuffled order, `greedy_van_repair` now:

1. calls `_local_target_van` exactly once;
2. calls `_best_van_move_on_route` for that route only;
3. calls `_best_drone_move` with `allowed_launch_van_ids={target_van_id}`;
4. keeps all legal recovery routes, including cross-van recovery;
5. stable-sorts the at-most-two best mode moves by the unchanged cost delta;
6. applies the first move through the existing `_apply_move`;
7. leaves the customer unassigned when both scoped generators return no move.

The existing `rng.shuffle(repaired.unassigned)` call is unchanged. Van is still appended before drone, so equal-cost stable tie behavior is unchanged.

## Reused behavior

- Van delta: `_van_insert_cost` and existing fixed-cost logic.
- Van feasibility: `_can_van_insert` and `_van_insert_hard_feasible`.
- Drone delta: existing sortie distance and fixed-cost logic.
- Drone feasibility: `_drone_insert_hard_feasible` and its existing cache/dedup path.
- Apply: `_apply_move`.
- Finalization: `_finalize_repair` / existing sortie consolidation.

## Instrumentation

`greedy_van_repair` has an optional `trace_collector` callback. It receives customer-level target, visited-route, candidate-count, launch/recovery, selection, and cost fields. It is disabled by default, does not consume RNG, does not modify objective input, and does not write State metadata.

## Greedy-drone compatibility

Before Stage 2B, `greedy_drone_repair` used `greedy_van_repair` as a global van-only fallback. Because Greedy-drone is outside this stage's change scope, Local detects that immediate caller through the existing repair stack and executes the previous global van-only body. The Greedy-drone function and registry are unchanged.

## Deliberately unchanged modules

Global/best-mode repair, Regret, Cascade, Greedy-drone source, destroy operators, registry, checker, objective, initial solution, SA, ALNS loop, adaptive weights, data/config defaults, evaluation, plots, and Stage 2A audit artifacts were not modified.
