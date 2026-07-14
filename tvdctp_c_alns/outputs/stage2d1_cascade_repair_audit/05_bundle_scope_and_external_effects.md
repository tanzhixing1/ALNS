# Bundle scope and external effects

## Active reconstruction boundary

Candidate generation derives its active van IDs, route-segment nodes, sortie IDs, launch/recovery links, carrier links, and coordination IDs exclusively from `bundle.affected_structure_scope` and its matching snapshots.

- Van block candidates insert the whole bundle only within captured start/end segment bounds.
- Drone candidates require both launch and recovery vans to be affected vans and both anchor nodes to exist in their captured route segments.
- Snapshot reconstruction uses only recorded bundle customer service, affected routes, affected sorties, launch/recovery, and carrier records.

## External structural guard

Before a candidate is accepted, the implementation compares a structural projection of the base and candidate States. It requires unchanged:

- selected transshipment, truck route, tractor and container routes;
- all van routes outside the affected vans;
- bundle-external service modes and order/container/warehouse associations;
- every bundle-external sortie identity, including customer sequence, launch, recovery, drone and carrier vans;
- van homes, drone initial carriers, and drone home warehouses.

For affected van routes, removing the current bundle customers from the before/after route must produce the identical external sequence. This distinguishes an allowed bundle insertion (which necessarily shifts absolute numeric indices of downstream nodes) from an active reorder/reassignment of external customers.

Timing, departure, waiting, load, and cache/diagnostic metadata are excluded from the structural projection because canonical propagation may update them passively.

## Consolidation

Cascade repair no longer calls `_finalize_repair()` or global `consolidate_drone_sorties()`. The selected complete bundle strategy already supplies its scoped sortie reconstruction. Therefore no post-selection consolidation can merge, split, or rewrite an unrelated sortie. Global/Local/Regret retain their existing finalization behavior unchanged.

Focused evidence checks the external structural projection and explicitly compares unrelated sortie customer sequence, launch/recovery, physical drone, and carrier vans.
