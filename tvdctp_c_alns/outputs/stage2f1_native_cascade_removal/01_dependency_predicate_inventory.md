# Native Cascade Customer Dependency Predicate Inventory

This inventory is closed before production modification. Only the two exact predicates below are admitted. There is no generic coordination catch-all.

| Predicate ID | Projection fields | Source extraction | Target extraction | Direction | Structural rank | Multiple-occurrence resolution | Provenance | Positive fixture | Negative fixture | Boundary fixture | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NCD-A-SAME-SUBROUTE | `drone_sortie_facts[*].{customer_ids,launch_node,recovery_node,sortie_id}` plus authoritative customer-ID allowlist | Every distinct customer node in `[launch, *customer_ids, recovery]` | Every other distinct customer node in the same sequence | Symmetric (materialized as both directed arcs) | `(sortie_index, target_position, source_position, 0)` | For the same predicate/source/target, retain the lexicographically minimum `(rank, provenance)` across all legal occurrences | `sortie_id:same-subroute:source_position->target_position` | `test_same_subroute_predicate_extracts_customers_and_symmetric_edges` | `test_same_subroute_predicate_excludes_unrelated_customer` | `test_same_subroute_predicate_excludes_non_customer_anchors_and_deduplicates_occurrences` | IMPLEMENT — MED-2 / MED-3; paper dependency scope is PARTIAL |
| NCD-B-LAUNCH-RECOVERY | `coordination_edge_facts[*]` with exact `edge_kind == "launch-recovery-order"`, exact `node:<id>` endpoints, and matching sortie rank | Customer ID parsed from exact source `node:<id>` | Customer ID parsed from exact target `node:<id>` | Directed source→target | `(sortie_index, target_position, source_position, 1)` | For the same predicate/source/target, retain the lexicographically minimum `(rank, provenance)` | exact `coordination_edge_facts.edge_id` | `test_launch_recovery_predicate_preserves_direction_rank_and_provenance` | `test_launch_recovery_predicate_does_not_reverse_directed_edge` | `test_launch_recovery_predicate_requires_two_customer_endpoints` | IMPLEMENT — MED-2 / MED-3; paper direction is PARTIAL |
| NCD-C-CARRIER-LINK | `carrier_transfer_facts` | Not available as a customer endpoint | Not available as a customer endpoint | Cannot be established without inference | N/A | N/A | Carrier facts identify vans/drone/sortie, not two customers | N/A | `test_non_customer_coordination_edges_do_not_enter_customer_graph` | cross-van carrier transfer with warehouse/customer anchors | REJECT — KNOWN CONSERVATIVE REPRESENTATION GAP |
| NCD-D-RESOURCE-COORDINATION | `coordination_edge_facts` kinds `van-drone-launch` and `van-drone-recovery` | Resource entity, not customer | Resource entity, not customer | Resource direction only | N/A | N/A | exact resource edge IDs retained only by snapshots | N/A | `test_non_customer_coordination_edges_do_not_enter_customer_graph` | van/drone IDs that contain numeric text | REJECT — non-customer structures must not enlarge R* |

## Rank and endpoint rules

- `sortie_index` is the stable pre-destroy tuple traversal index in `StructuralProjection.drone_sortie_facts`.
- Positions are the pre-destroy sequence `[launch, *sortie customer_ids, recovery]`; repeated customer nodes use their minimum legal position.
- Graph endpoints must be members of the explicit `data.customers` allowlist. Warehouse, depot, van, drone, route, sortie, container, transshipment and carrier identifiers are never converted to customer nodes.
- Duplicate structural occurrences retain the minimum lexicographic rank; provenance breaks an otherwise exact rank tie.
- NCD-A and NCD-B may both describe the same ordered pair. They remain separate audit edges because their predicate IDs and provenance differ; closure membership deduplicates the target customer.

## Classification

- Recursive fixed-point closure and final `R*`: **PAPER EXPLICIT**.
- Concrete predicates and ranks: **APPROVED MINIMAL ENGINEERING DECISION** under MED-2/MED-3.
- Same-subroute and launch/recovery dependency meaning/direction: **PAPER PARTIAL**.
- Exact tie handling and Python representation: **PAPER UNSPECIFIED**.
