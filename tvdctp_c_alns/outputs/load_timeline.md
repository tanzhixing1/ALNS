# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 3 -> 5 -> 4 -> 3 |
| used_drones | 1 |
| used_drone_sorties | 2 |
| total_cost | 541.725 |
| waiting_cost_reported | 77.039 |
| drone_energy_kwh | 19.124 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3 | transshipment | 107.049 | 74.000 | 0.000 | 74.000 | 0.000 | 0.000 | 0.000 | 0.000 | 74.000 | 0.000 | 74.000 | True |
| 1 | 5 | customer | 138.106 | 74.000 | 0.000 | 74.000 | 13.000 | 4.000 | 28.000 | 0.000 | 33.000 | 4.000 | 37.000 | True |
| 2 | 4 | customer | 156.018 | 33.000 | 4.000 | 37.000 | 16.000 | 9.000 | 17.000 | 31.000 | 0.000 | 44.000 | 44.000 | True |
| 3 | 3 | transshipment | 258.953 | 0.000 | 44.000 | 44.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 44.000 | 44.000 | True |
| 0 | 3 | transshipment | 107.049 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |
| 1 | 3 | transshipment | 107.049 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_4 | launch | 4 |  | 2 | 186.459 | 17.000 | 0.000 | 17.000 | 0.000 | 0.000 | 17.000 | 0.000 | 17.000 | 0.000 | 0.000 | True | True |
| 1 | drone_4 | serve_customer | 9 | 4->9 |  | 207.154 | 17.000 | 0.000 | 17.000 | 9.000 | 1.000 | 8.000 | 1.000 | 9.000 | 3.856 | 3.856 | True | True |
| 1 | drone_4 | serve_customer | 6 | 9->6 |  | 216.220 | 8.000 | 1.000 | 9.000 | 8.000 | 1.000 | 0.000 | 2.000 | 2.000 | 1.085 | 4.941 | True | True |
| 1 | drone_4 | recovery | 4 | 6->4 | 2 | 244.404 | 0.000 | 2.000 | 2.000 | 0.000 | 0.000 | 0.000 | 2.000 | 2.000 | 1.729 | 6.670 | True | True |
| 2 | drone_4 | launch | 5 |  | 1 | 138.106 | 28.000 | 0.000 | 28.000 | 0.000 | 0.000 | 28.000 | 0.000 | 28.000 | 0.000 | 0.000 | True | True |
| 2 | drone_4 | serve_customer | 7 | 5->7 |  | 142.401 | 28.000 | 0.000 | 28.000 | 17.000 | 11.000 | 11.000 | 11.000 | 22.000 | 1.194 | 1.194 | True | True |
| 2 | drone_4 | serve_customer | 8 | 7->8 |  | 165.628 | 11.000 | 11.000 | 22.000 | 11.000 | 18.000 | 0.000 | 29.000 | 29.000 | 5.296 | 6.490 | True | True |
| 2 | drone_4 | recovery | 4 | 8->4 | 2 | 186.459 | 0.000 | 29.000 | 29.000 | 0.000 | 0.000 | 0.000 | 29.000 | 29.000 | 5.965 | 12.455 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_4 | 4 | 2 | 244.404 | 0.000 | 2.000 | 2.000 | True |
| 2 | drone_4 | 4 | 2 | 186.459 | 0.000 | 29.000 | 29.000 | True |

## Physical Drone Routes
- physical_drone_4: 3 -> 5 -> 7 -> 8 -> 4 -> 9 -> 6 -> 4

