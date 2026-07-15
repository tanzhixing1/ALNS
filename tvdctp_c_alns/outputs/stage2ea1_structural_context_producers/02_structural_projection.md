# Immutable structural projection

`capture_structural_projection(state)` is a read-only allowlist projection. It
does not call RNG, objective, checker, operator selection, cache helpers or
State mutation helpers.

Included business structure:

- unassigned and service mode;
- ordered van routes, positions and adjacent segments;
- ordered drone sorties and ordered sortie customers;
- launch/recovery nodes, vans and positions;
- drone initial/current carriers and carrier transfers;
- launch/recovery/coordination edge identities;
- order/container assignment, container routes, tractor routes and warehouse
  context;
- selected transshipment, truck route, vehicle homes;
- only the business metadata allowlist `route_endpoints` and
  `warehouse_ready_time`.

Excluded:

- active `RemovalStructuralContext` metadata and the context itself;
- Cascade contracts/bundles/repair diagnostics;
- objective/checker caches and timing diagnostics;
- runtime/profile counters, addresses, UUIDs and nondeterministic reprs.

All dict/list/set descendants are converted to tagged immutable tuples with
typed stable keys. Projection capture before and after destroy is therefore
independent of later State mutation and cannot recursively include its context.
