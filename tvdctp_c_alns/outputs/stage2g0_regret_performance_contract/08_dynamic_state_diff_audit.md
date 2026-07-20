# Dynamic State Diff Audit

Recursive base-vs-candidate projections cover route/sortie structures,
assignments/service state, unassigned, carrier facts, complete timing, cost
components and checker result. Audited representatives:

- `van_insertion`: observed `cost_breakdown;feasible;service_mode;timing;unassigned;van_route;van_routes;violations`; mutation 29.57%; false negatives `none`; checker `True`.
- `same_van_drone`: observed `cost_breakdown;drone_sorties;feasible;service_mode;timing;unassigned;violations`; mutation 16.02%; false negatives `none`; checker `True`.
- `cross_van_flexible_docking`: observed `cost_breakdown;drone_sorties;feasible;service_mode;timing;unassigned;violations`; mutation 43.88%; false negatives `none`; checker `True`.
- `high_floor_drone_customer`: observed `cost_breakdown;drone_sorties;feasible;service_mode;timing;unassigned;violations`; mutation 16.45%; false negatives `none`; checker `True`.
- `linked_multi_customer_relaunch`: observed `cost_breakdown;drone_sorties;feasible;service_mode;timing;unassigned;violations`; mutation 9.09%; false negatives `none`; checker `True`.
- `capacity_exact_boundary`: observed `cost_breakdown;feasible;service_mode;timing;unassigned;van_route;van_routes;violations`; mutation 29.57%; false negatives `none`; checker `True`.
- `time_window_exact_boundary`: observed `cost_breakdown;feasible;service_mode;timing;unassigned;van_route;van_routes;violations`; mutation 35.31%; false negatives `none`; checker `True`.

The capacity fixture sets van capacity exactly to the candidate route payload
(slack 0 kg). The time-window fixture sets latest exactly to candidate service
start (slack 0 minutes). Both remain hard-feasible. The linked/relaunch row is
the actual heavy selected move serving `[13, 21]` with a previously used physical
drone.

Total static-prediction false negatives: **0**. Conservative
false positives occur because a dependency-closure member need not numerically
change in every concrete instance. Decision: **AFFECTED-SCOPE PREDICTION SAFE for
the audited candidate classes**, subject to the explicit global/unknown checker
limits in reports 11 and 13.
