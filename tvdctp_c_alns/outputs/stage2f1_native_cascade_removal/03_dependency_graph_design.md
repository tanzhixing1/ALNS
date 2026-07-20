# Pre-destroy Customer Dependency Graph Design

## Source and boundary

`_build_native_cascade_customer_dependency_graph` reads the immutable `StructuralProjection` captured before any removal mutation. Its node universe is exactly the explicit `data.customers` allowlist. It consumes zero RNG and does not call objective, feasibility, repair, or `_remove_customer`.

Only the closed inventory is implemented:

- `NCD-A-SAME-SUBROUTE`: symmetric arcs among distinct customer nodes in `[launch, *sortie customers, recovery]`.
- `NCD-B-LAUNCH-RECOVERY`: directed arc for exact `CoordinationEdgeFact(edge_kind="launch-recovery-order")` when both `node:<id>` endpoints are customers.

No generic catch-all exists. Van, drone, warehouse, depot, route, sortie, container and carrier identifiers never become graph nodes. Truck/van/resource structure remains snapshot scope only.

## Stable identity and rank

Edges retain predicate ID, source/target customer, structural rank and provenance. The stable neighbor key is:

```text
structural rank → target customer ID → predicate ID → provenance
```

For repeated legal occurrences of the same predicate/source/target, the minimum lexicographic `(rank, provenance)` is retained. The focused repeated-pair fixture confirmed both NCD-A and NCD-B select pre-destroy sortie rank 0.

## Canonical fixture graph

The canonical Stage 2F.0 fixture yields five retained edges: four symmetric same-subroute arcs and one launch/recovery self-loop. The warehouse launch in the cross-van sortie is excluded, while its customer recovery anchor remains a customer node.

Classification:

- Customer dependency meaning: **PAPER PARTIAL**.
- Concrete predicates, rank and provenance: **APPROVED MINIMAL ENGINEERING DECISION**.
- Exact tie handling: **PAPER UNSPECIFIED**.
