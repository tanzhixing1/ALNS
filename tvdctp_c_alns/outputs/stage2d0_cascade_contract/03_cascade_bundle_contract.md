# Minimum structured Cascade bundle contract

The selected representation is an immutable frozen dataclass graph rooted at `CascadeBundleSnapshot`. Tuple-valued fields make canonical serialization deterministic; `TVDState.copy()` still deep-copies the containing metadata list and contract dictionary. No complete `TVDState` is stored.

| Field | Required | Captured before removal | Why needed | Stage |
|---|---|---|---|---|
| `schema_version` | YES | YES | Reject incompatible readers | 2D.0 |
| `bundle_id` | YES | YES | Deterministic per-destroy/per-index identity | 2D.0 |
| `source_operator` / `source_destroy_call_id` | YES | YES | Origin and lifecycle validation | 2D.0 |
| `source_state_fingerprint` | YES | YES | Bind snapshot to the source business State | 2D.0 |
| `customer_ids` | YES | YES | Exact bundle membership | 2D.0 |
| `dependency_order` | YES, implementation field | YES | Preserve existing bundle order without redesign | 2D.0; Paper unspecified |
| Dependency closure/propagation rule | NO | N/A | Determines how `R*` and bundles are formed | DEFER TO STAGE 2F |
| `customer_service_snapshots` | YES | YES | Original service mode; exact van location when present; order/container/warehouse association | 2D.0 |
| `affected_route_segments` | YES when associated | YES | Minimal bounded source route segment plus original absolute affected positions | 2D.0 |
| `removed_drone_subroutes` | YES when associated | YES | Drone identity and exact launch–customers–recovery sub-route | 2D.0 |
| `launch_recovery_snapshots` | YES when associated | YES | Launch/recovery nodes, vans, positions, same/cross-van status | 2D.0 |
| `carrier_transfer_snapshots` | YES when associated | YES | Initial carrier, launch carrier, recovery carrier, and transfer status | 2D.0 |
| `truck_warehouse_context` | YES | YES | Selected warehouse and affected container decision context | 2D.0 |
| `affected_structure_scope` | YES | YES | Explicit IDs for actively reconstructable truck context, van segments, sub-routes, links, and coordination edges | 2D.0 |
| Creation timestamp / UUID | NO | NO | Would make equivalent destroys nondeterministic | Excluded |
| Full State copy | NO | NO | Overweight and evades a structured boundary | Excluded |

Route snapshots contain only the smallest contiguous source segment spanning affected positions plus one boundary node on each side. Missing source fields remain `None`/unresolved; no default van, drone, carrier, launch, or recovery is invented.

`dependency_order` is exactly the current customer-list order and is labelled `current implementation order; Paper unspecified`. Cascade dependency propagation and sorting were not changed to obtain it.
