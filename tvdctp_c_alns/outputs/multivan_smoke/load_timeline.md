# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 2 -> 7 -> 4 -> 3 |
| used_drones | 2 |
| used_drone_sorties | 2 |
| total_cost | 818.247 |
| waiting_cost_reported | 34.953 |
| drone_energy_kwh | 5.980 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | transshipment | 76.870 | 42.000 | 0.000 | 42.000 | 0.000 | 0.000 | 9.000 | 1.000 | 33.000 | 1.000 | 34.000 | True |
| 1 | 7 | customer | 151.547 | 33.000 | 1.000 | 34.000 | 17.000 | 11.000 | 0.000 | 0.000 | 16.000 | 12.000 | 28.000 | True |
| 2 | 4 | customer | 174.476 | 16.000 | 12.000 | 28.000 | 16.000 | 9.000 | 0.000 | 0.000 | 0.000 | 21.000 | 21.000 | True |
| 3 | 3 | transshipment | 189.026 | 0.000 | 21.000 | 21.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 21.000 | 21.000 | True |
| 0 | 2 | transshipment | 76.870 | 32.000 | 0.000 | 32.000 | 0.000 | 0.000 | 11.000 | 18.000 | 21.000 | 18.000 | 39.000 | True |
| 1 | 6 | customer | 137.806 | 21.000 | 18.000 | 39.000 | 8.000 | 1.000 | 0.000 | 0.000 | 13.000 | 19.000 | 32.000 | True |
| 2 | 5 | customer | 190.421 | 13.000 | 19.000 | 32.000 | 13.000 | 4.000 | 0.000 | 0.000 | 0.000 | 23.000 | 23.000 | True |
| 3 | 3 | transshipment | 221.478 | 0.000 | 23.000 | 23.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 23.000 | 23.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_2 | launch | 2 |  | 0 | 76.870 | 11.000 | 0.000 | 11.000 | 0.000 | 0.000 | 11.000 | 0.000 | 11.000 | 0.000 | 0.000 | True | True |
| 1 | drone_2 | serve_customer | 8 | 2->8 |  | 85.243 | 11.000 | 0.000 | 11.000 | 11.000 | 18.000 | 0.000 | 18.000 | 18.000 | 1.142 | 1.142 | True | True |
| 1 | drone_2 | recovery | 2 | 8->2 | 0 | 93.616 | 0.000 | 18.000 | 18.000 | 0.000 | 0.000 | 0.000 | 18.000 | 18.000 | 1.630 | 2.771 | True | True |
| 2 | drone_0 | launch | 2 |  | 0 | 76.870 | 9.000 | 0.000 | 9.000 | 0.000 | 0.000 | 9.000 | 0.000 | 9.000 | 0.000 | 0.000 | True | True |
| 2 | drone_0 | serve_customer | 9 | 2->9 |  | 95.454 | 9.000 | 0.000 | 9.000 | 9.000 | 1.000 | 0.000 | 1.000 | 1.000 | 2.224 | 2.224 | True | True |
| 2 | drone_0 | recovery | 2 | 9->2 | 0 | 114.037 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.985 | 3.209 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_2 | 2 | 0 | 93.616 | 0.000 | 18.000 | 18.000 | True |
| 2 | drone_0 | 2 | 0 | 114.037 | 0.000 | 1.000 | 1.000 | True |

## Physical Drone Routes
- physical_drone_0: 2 -> 9 -> 2
- physical_drone_2: 2 -> 8 -> 2

