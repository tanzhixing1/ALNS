# Drone symmetry analysis

## Classification

**B. NOT STRICTLY SYMMETRIC**

The configured capacity, endurance/energy parameters, speed, variable cost, and
fixed cost are shared. That parameter equality is not state symmetry.

The model stores named resources in `state.drone_initial_carrier` and binds every
sortie to a concrete `drone_id`. `operators._drone_physical_local_check()` groups
existing and candidate sorties by that ID, orders each drone's records, derives
its current carrier and available time, rejects carrier/order/warehouse-return
conflicts, and then checks the concrete candidate. `compute_timing()` and the
canonical checker also retain per-ID location, availability, launch/recovery,
and continuity state. Objective fixed cost is based on the set of concrete IDs
used, so choosing an already-used versus idle drone can change objective and
future state.

| Property | Same by configuration? | Same in a live State? |
| --- | --- | --- |
| Capacity | Yes | Yes |
| Endurance / energy | Yes | Yes |
| Variable and fixed cost parameters | Yes | No guarantee of equal fixed-cost delta |
| Initial carrier | Per-ID mapping | No general equality |
| Existing task | N/A | No |
| Available time | N/A | No |
| Current carrier after recovery | N/A | No |
| Launch/recovery eligibility | N/A | Depends on the concrete history |

Therefore `_first_drone_for_van()` was not a proven lossless symmetry reduction.
The decisive real-State counterexample is recorded in
`02_multidrone_counterexample.md`.
