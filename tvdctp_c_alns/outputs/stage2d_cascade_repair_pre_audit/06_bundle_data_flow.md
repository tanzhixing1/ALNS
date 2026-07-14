# Bundle data flow

## Paper flow

```text
feasible current solution S
  -> base destroy creates R(0)
  -> structural dependency closure creates R*
  -> remove customers + associated route/sub-route/coordination structures
  -> partition R* by dependency into customer bundles B
  -> for each B construct joint Omega(B)
  -> choose min full-objective strategy
  -> jointly reconstruct associated structures
```

## Current Cascade-removal flow

`cascade_aware_removal`:

1. Copies the State and randomly selects initial served customers.
2. `_cascade_dependencies` expands only through current drone sorties. It includes sortie customers and customer launch/recovery nodes, excluding route endpoints.
3. It does not derive truck dependencies, warehouse reassignment dependencies, general van-route segments, downstream receiving-route segments, containers, or explicit timing relations.
4. It creates bundle lists by intersecting each pre-removal drone sortie's related customer set with the removal set; all remaining customers become singleton bundles.
5. It removes customers and associated touched sorties through `_remove_customer`.
6. It writes only:
   - `metadata["cascade_removed"]: List[int]`
   - `metadata["cascade_bundles"]: List[List[int]]`

Observed example with three initial drone sorties:

```text
sortie customer 10 launched at customer 7 -> bundle [7, 10]
cross-van sortie customer 11 recovered at customer 8 -> bundle [8, 11]
unrelated removed customers -> singleton bundles
```

No removed route segment, original position, original service mode, sortie snapshot, launch/recovery resource relation, carrier state, truck relation, or warehouse relation is passed to repair.

## Metadata loss and staleness

The metadata is not lost across `State.copy`; it is deep-copied. The opposite problem exists: repair does not consume or clear it, and non-cascade destroy operators do not clear or replace it.

Observed sequence:

```text
accepted-like repaired State metadata: [[7, 10]]
later non-cascade destroy unassigned: [10, 9, 12]
metadata after non-cascade destroy: [[7, 10]]
intersection used by Cascade repair: [[10]]
metadata_cleared: False
```

Thus Cascade repair may receive stale bundles from an earlier iteration. Its final all-unassigned sweep hides the missing coverage instead of detecting the contract violation.

## Current repair fallback flow

```text
cascade_bundles truthy
  -> use stale/current customer lists after intersection with unassigned
cascade_bundles missing/empty
  -> treat all unassigned as one bundle
either path
  -> candidate completion expands to all unassigned
```

## Audit conclusion

The current State can transport customer-list bundles, but it cannot transport the structural context required for paper-level coordinated reconstruction. Bundle formation and dependency propagation are Stage 2F responsibilities. Stage 2D should define and validate an explicit input contract, but must not invent missing removal semantics.
