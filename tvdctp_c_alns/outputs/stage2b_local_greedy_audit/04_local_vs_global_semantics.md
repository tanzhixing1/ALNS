# Local vs Global semantics

| Dimension | Local greedy | Existing Global/best-mode path |
| --- | --- | --- |
| Route selection | One deterministic target before candidate costing | No target; all repair routes are enumerated |
| Van positions | Target route only | Every position on every legal route, including existing unused-vans behavior |
| Drone launch | Target van/route only | Every launch van/route |
| Drone recovery | Every currently legal same-van or cross-van recovery | Every currently legal same-van or cross-van recovery |
| Mode choice | Cheapest hard-feasible van/drone move in the local set | Cheapest hard-feasible move in the global set |
| Scoped failure | Customer remains unassigned | Other routes can still supply a candidate |

The core distinction is search scope, not a new objective or feasibility definition. The focused controlled test makes route B cheaper: `_best_van_move` selects B, while Local can only select target route A. A separate failure test makes A infeasible and B feasible: Local leaves the customer unassigned while Global returns B.
