# Target route rule

`_local_target_van(customer, state)` returns one `target_van_id` and a diagnostic source label. It never evaluates insertion positions, feasibility, distance, objective delta, or route cost.

## Paper-explicit semantic requirement

Local must preselect exactly one target route and search only that route's van positions and target-related drone launches. Selecting a route by first evaluating every route would still be Global and is prohibited.

## Existing-state rules inherited by Stage 2B

Priority 1 uses route ownership when already present:

- metadata mappings named `previous_van_assignment`, `previous_route_ownership`, `previous_service_route`, `bundle_anchor_route`, or `originating_route`;
- explicit route fields already present in the customer's `order_assignment`.

Priority 2 follows the existing order/container mapping:

`order_assignment[customer].container_id` -> `container_routes[container_id].destination_warehouse` -> first existing route whose `van_home` is that warehouse.

If the container route does not expose the destination, `assigned_transshipment` is used as the warehouse mapping.

## Stage 2B engineering fallback

When neither ownership nor warehouse mapping resolves an existing route, the selector returns the first existing route in stable numeric van order (`van_0`, `van_1`, ...; string order for nonstandard IDs).

This fallback is a minimal deterministic engineering choice, not a claim about an explicit paper rule. It is isolated in one helper so a later evidence-backed route-ownership policy can replace it.

Only routes already present in `state.van_routes` (or the legacy primary route) are candidates. Local does not call `_repair_van_routes`, so it does not add an unused route after a scoped failure.
