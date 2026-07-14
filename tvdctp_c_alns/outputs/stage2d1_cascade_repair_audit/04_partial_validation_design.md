# Canonical partial-validation design

No capacity, time-window, energy, carrier, synchronization, or route-consistency rule was reimplemented.

`_validate_cascade_candidate()` is a thin wrapper around the existing `check_solution_feasible()`:

1. call the canonical full checker and retain its complete violation list;
2. require `State.unassigned` to equal the explicitly supplied `allowed_unassigned` set;
3. require every current bundle customer to be absent from `State.unassigned`;
4. ignore only the exact canonical string `unassigned customers remain: [...]`, and only when the listed State set exactly equals `allowed_unassigned`;
5. retain every other violation without category-wide filtering.

Thus the wrapper never ignores duplicate service, a missing bundle customer, wrong mode, time window, van load, drone payload/energy, carrier continuity, synchronization, route consistency, or container/warehouse inconsistency.

The full checker signature and implementation were not changed. Ordinary final validation retains its Stage 2D.0 semantics. Focused tests prove the wrapper invokes the canonical checker, accepts only explicit external missing service, rejects a bundle customer that remains unassigned, and retains representative duplicate/timing/load/energy/carrier violations.
