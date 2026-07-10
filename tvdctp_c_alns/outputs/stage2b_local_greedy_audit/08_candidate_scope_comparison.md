# Candidate scope comparison

Fixed real toy instance: 6 customers, seed 42, customer 9 removed from the initial solution, same State and customer for both generators.

| Metric | Local | Global |
| --- | ---: | ---: |
| Visited van routes | `van_0` | `van_0`, `van_1` |
| Drone launch routes | `van_0` | `van_0` (only active route in State) |
| Van candidates | 6 | 7 |
| Drone candidates | 27 | 27 |
| Total candidates | 33 | 34 |
| Selected route | `van_0` | `van_0` |
| Selected mode | van | van |
| Cost delta | 4.252735686300749 | 4.252735686300749 |
| Applied State full feasible | true | true |

Therefore `Local visited routes < Global visited routes` and `Local total candidates < Global total candidates` on a real fixture.

The controlled two-route semantic fixture gives the stronger quality distinction: route B is cheaper than target A, Global selects B, and Local selects A. When A is made infeasible while B remains feasible, Local leaves the customer unassigned and Global still returns B.
