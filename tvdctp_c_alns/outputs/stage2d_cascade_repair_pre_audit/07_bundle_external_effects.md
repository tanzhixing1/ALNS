# Bundle-external effects

## Bundle-external unassigned customers

They are actively repaired. This is caused by `_finish_repair` over the full `unassigned` list and the final global cleanup sweep. It is not a passive consequence of bundle insertion.

## Bundle-external served customers: active structural effects

Current bundle insertion does not explicitly remove and reinsert already served external customers. Their service-mode mapping and van assignment normally remain unchanged. However:

- Inserting bundle or external-unassigned customers into a route changes adjacent arcs and absolute route indices of already served nodes.
- Drone moves can use served external nodes/routes as launch and recovery anchors.
- `_finalize_repair` invokes `consolidate_drone_sorties` over the entire feasible State, not only bundle-associated sorties.
- Consolidation may merge unrelated pre-existing sorties, combine customer sequences, retain the first sortie's drone/launch and the later sortie's recovery, and therefore actively change sortie structure and carrier/launch/recovery relationships for served external drone customers.

The focused consolidation test passed and confirms that this global structural rewrite is reachable.

## Passive constraint propagation

Hard-feasibility checks and the final objective/checker recompute route times, drone timing, waiting, and load effects. Bundle insertion may therefore change downstream arrival, departure, waiting, and load timelines without changing a downstream customer's service identity. Such changes are necessary passive propagation, not by themselves evidence that the customer was actively repaired.

## Probe result

In the van-only Case A, external served customer modes did not change, but absolute route positions changed:

```text
customer 8: van_0 position 3 -> 4
customer 10: van_0 position 2 -> 3
```

This was caused by inserting other customers before them; their relative order and route assignment were preserved.

## Paper alignment

- The paper supports structural adjustment of **associated** launch and receiving van routes.
- The paper supports downstream feasibility/timing propagation.
- The paper does not support arbitrary active rewrites of unrelated served structures.
- The exact boundary for served anchor nodes that are associated but not members of `B` is **Paper unspecified** and needs an implementation contract.
