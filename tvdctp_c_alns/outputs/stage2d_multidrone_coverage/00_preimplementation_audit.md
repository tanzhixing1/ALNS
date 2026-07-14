# Stage 2D multi-drone preimplementation audit

Baseline: `999ba977f6ea36d7bcf02a665accc56f312e11c4`

This report was written before any production-code change.

## Classification

**B. NOT STRICTLY SYMMETRIC**

The fleet parameters are global, so named drones share configured payload,
endurance, battery, speed, distance cost, and fixed cost. They are nevertheless
not state-symmetric. Existing sorties are grouped and sequenced by concrete
`drone_id`; each id has its own initial carrier, derived current carrier,
availability time, warehouse-return state, and sortie history.

## Code evidence

- `operators._first_drone_for_van` returns the first insertion-ordered id whose
  `state.drone_initial_carrier` equals the launch van. It does not inspect
  existing sorties, current carrier, availability time, or warehouse return.
- Both `_best_drone_move_for_customers` and
  `_enumerate_feasible_drone_moves_for_customers` use that single id.
- `_drone_physical_local_check` groups records by concrete `drone_id`, derives
  current carrier from each id's sortie sequence, rejects launch from the wrong
  carrier, rejects continuation after warehouse recovery, and carries forward
  a per-id availability time.
- `feasibility.compute_timing` maintains `drone_location` and
  `drone_available_time` per concrete id and honors a requested id.
- `check_solution_feasible` validates unknown ids, per-id carrier continuity,
  launch/recovery ordering, overlapping chronology, continuation after
  warehouse return, and per-id warehouse launch/return counts.
- Objective parameters are shared, but fixed usage is counted by the set of
  named physical drone ids. A second named drone can therefore change current
  and future fixed usage even when flight distance is identical.
- Regret and Cascade share `_enumerate_feasible_drone_moves_for_customers`:
  Regret reaches it through `_enumerate_feasible_drone_moves`, while Cascade
  passes `list(bundle.dependency_order)` directly.

The separate same-named helper in `initial_solution.py` is outside the allowed
production scope of this audit and is not the repair-candidate helper.

## Required questions

| Property | Same for drones on one initial van? | Evidence |
|---|---|---|
| Capacity | Yes, configured globally | `config.fleet.drone_capacity_kg` |
| Endurance | Yes, configured globally | `config.fleet.drone_endurance_km` |
| Battery/energy parameters | Yes, configured globally | `FleetConfig` |
| Distance and fixed cost parameters | Yes, configured globally | `CostConfig` |
| Initial carrier | May match within one van, but is id-bound | `drone_initial_carrier` |
| Current carrier | No | derived per id from prior recovery van/warehouse |
| Availability | No | per-id `drone_available_time` and prior recovery time |
| Existing sortie assignment | No | sorties contain concrete `drone_id` |
| Launch/recovery eligibility | No | depends on per-id carrier and history |

The canonical and local checkers depend on `drone_id` for carrier continuity,
existing-task order, availability chronology, warehouse return, and resource
counts. Therefore the first id can be infeasible while another initially
co-carried id is feasible.

## Decisive real-state counterexample

The coordinated Stage 2D fixture was changed only in memory:

- `drone_0` and `drone_1` both initially belong to `van_0`;
- `drone_0` already has a real sortie from `van_0` and recovers at the terminal
  warehouse through `van_1`;
- `drone_1` has no sortie and remains on `van_0`;
- customer `9` is the only unassigned customer.

The canonical checker on the base State returned only:

```text
unassigned customers remain: [9]
```

The old enumerator returned candidates with `drone_2` but no candidate with
`drone_1`, because `drone_0` is the first id for `van_0` and every attempted
continuation for that id is rejected after warehouse return. Independently
constructing the same launch/recovery candidate with `drone_1` passed the
existing hard-feasibility function, and applying it produced a State accepted
by the full canonical checker with zero violations.

```text
first id for van_0: drone_0
old returned ids: [drone_2]
old returned drone_1: false
drone_1 candidate hard-feasible: true
full checker after applying drone_1 candidate: true, []
```

**MULTI-DRONE COVERAGE BUG CONFIRMED**

## Conditional-fix decision

Enter the authorized minimal repair-candidate fix. Enumerate a safe superset of
named drones that can be associated with the launch van through initial carrier
or an existing non-warehouse recovery, then retain candidates only through the
existing hard-feasibility logic. Do not introduce a replacement availability
model, change checker semantics, prune by cost, or modify the Cascade candidate
families.
