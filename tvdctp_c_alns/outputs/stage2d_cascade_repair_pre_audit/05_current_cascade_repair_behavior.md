# Current Cascade repair behavior

## Input and initial scope

The function copies its input State. It reads `metadata["cascade_bundles"]`; if the key is missing, empty, or otherwise false, it replaces the bundle input with a single bundle containing every current `unassigned` customer. It never validates `cascade_removed`, bundle coverage, freshness, disjointness, or origin destroy operator.

Each metadata bundle is filtered to customers still in `unassigned` and sorted high-floor first, then customer ID. Bundle order itself remains metadata order.

## What is tried for a bundle

The current candidate set is not paper-level `Omega(B)`. It contains:

1. Sequential all-van insertion using each customer's best van move.
2. Sequential “best mode” insertion using at most one best van and one best drone representative per current customer.
3. One drone sortie containing the whole bundle.
4. For bundle sizes 2-3 only, every non-empty proper customer subset as one drone sortie, with the rest inserted sequentially by van.

There is no complete joint reconstruction of truck routes, warehouse assignment, van routes, launch route, and receiving route. Existing served route nodes are used as anchors. The public Global, Local, and Regret repair functions are not called.

## Global completion hidden inside candidate evaluation

Every tentative bundle candidate is passed to `_finish_repair`, which repeatedly iterates over **the entire candidate State's `unassigned` list** and applies `_all_moves`. Only after this global completion does `_candidate_score` require full feasibility and score the whole objective.

Consequences:

- Bundle-external unassigned customers are repaired before a bundle candidate can be accepted.
- Failure of an unrelated external customer can make an otherwise repairable bundle candidate score as invalid.
- The first successfully evaluated bundle normally repairs every unassigned customer, so later metadata bundles become empty and are skipped.
- `_best_drone_move` may itself co-pack additional unassigned customers into a drone sortie, including customers outside the current bundle.

The known statement is therefore true: current Cascade repair repairs the bundle and then globally repairs all remaining unassigned customers. It happens inside `_best_bundle_repair -> _finish_repair` and again in the final cleanup loop.

## Fallbacks and failure

If no globally feasible candidate survives for a bundle, the function mutates its private `repaired` copy by trying `_all_moves` independently for each bundle customer. After all bundles, it performs another independent `_all_moves` sweep over every remaining unassigned customer.

If customers remain impossible, the function returns a State with `unassigned` still populated. It does not throw or roll back the whole repair. The ALNS loop evaluates the full objective/checker and rejects the infeasible candidate. The caller's original State is not polluted because the repair began from a copy.

## Diagnostic evidence

Case A used metadata bundle `[5, 6]` with customer `7` separately unassigned:

```text
input_unassigned [5, 6, 7]
output_unassigned []
external_C_served True
input_state_unchanged True
output_feasible True
```

Case D made bundle customer `5` high-floor while drones were disabled:

```text
output_unassigned [5]
input_state_unchanged True
output_feasible False
```

## Effective answer checklist

- Processes bundle first: nominally yes, but candidate evaluation immediately expands to all unassigned.
- Iterates all unassigned: yes, inside `_finish_repair` and final cleanup.
- Repairs bundle-external unassigned: yes.
- Calls another public repair fallback: no.
- Uses generic/global move generation: yes, `_all_moves` and `_best_*`.
- Can return unassigned: yes.
- Can pollute input State: no.
- Depends on removal metadata: optionally; missing metadata falls back globally.
- Can degenerate into ordinary greedy repair: yes.
