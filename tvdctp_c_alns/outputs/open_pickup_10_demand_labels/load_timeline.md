# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 2 -> 8 -> 10 -> 5 -> 6 -> 2 |
| used_drones | 1 |
| used_drone_sorties | 2 |
| total_cost | 520.152 |
| waiting_cost_reported | 38.919 |
| drone_energy_kwh | 20.974 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | transshipment | 76.870 | 71.000 | 0.000 | 71.000 | 0.000 | 0.000 | 19.000 | 0.000 | 52.000 | 0.000 | 52.000 | True |
| 1 | 8 | customer | 105.098 | 52.000 | 0.000 | 52.000 | 6.000 | 20.000 | 0.000 | 19.000 | 46.000 | 39.000 | 85.000 | True |
| 2 | 10 | customer | 156.080 | 46.000 | 39.000 | 85.000 | 13.000 | 9.000 | 0.000 | 0.000 | 33.000 | 48.000 | 81.000 | True |
| 3 | 5 | customer | 163.567 | 33.000 | 48.000 | 81.000 | 7.000 | 15.000 | 0.000 | 0.000 | 26.000 | 63.000 | 89.000 | True |
| 4 | 6 | customer | 169.633 | 26.000 | 63.000 | 89.000 | 5.000 | 7.000 | 21.000 | 0.000 | 0.000 | 70.000 | 70.000 | True |
| 5 | 2 | transshipment | 173.497 | 0.000 | 70.000 | 70.000 | 0.000 | 0.000 | 0.000 | 30.000 | 0.000 | 100.000 | 100.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | launch | 2 |  | 0 | 76.870 | 19.000 | 0.000 | 19.000 | 0.000 | 0.000 | 19.000 | 0.000 | 19.000 | 0.000 | 0.000 | True | True |
| 1 | 1 | serve_customer | 4 | 2->4 |  | 91.582 | 19.000 | 0.000 | 19.000 | 9.000 | 11.000 | 10.000 | 11.000 | 21.000 | 2.986 | 2.986 | True | True |
| 1 | 1 | serve_customer | 9 | 4->9 |  | 93.533 | 10.000 | 11.000 | 21.000 | 8.000 | 8.000 | 2.000 | 19.000 | 21.000 | 0.429 | 3.415 | True | True |
| 1 | 1 | serve_customer | 11 | 9->11 |  | 106.399 | 2.000 | 19.000 | 21.000 | 2.000 | 0.000 | 0.000 | 19.000 | 19.000 | 2.826 | 6.241 | True | True |
| 1 | 1 | recovery | 8 | 11->8 | 1 | 123.578 | 0.000 | 19.000 | 19.000 | 0.000 | 0.000 | 0.000 | 19.000 | 19.000 | 3.487 | 9.729 | True | True |
| 2 | 1 | launch | 6 |  | 4 | 169.633 | 21.000 | 0.000 | 21.000 | 0.000 | 0.000 | 21.000 | 0.000 | 21.000 | 0.000 | 0.000 | True | True |
| 2 | 1 | serve_customer | 7 | 6->7 |  | 188.067 | 21.000 | 0.000 | 21.000 | 7.000 | 1.000 | 14.000 | 1.000 | 15.000 | 4.049 | 4.049 | True | True |
| 2 | 1 | serve_customer | 12 | 7->12 |  | 191.883 | 14.000 | 1.000 | 15.000 | 11.000 | 20.000 | 3.000 | 21.000 | 24.000 | 0.647 | 4.697 | True | True |
| 2 | 1 | serve_customer | 13 | 12->13 |  | 197.409 | 3.000 | 21.000 | 24.000 | 3.000 | 9.000 | 0.000 | 30.000 | 30.000 | 1.352 | 6.049 | True | True |
| 2 | 1 | recovery | 2 | 13->2 | 5 | 215.046 | 0.000 | 30.000 | 30.000 | 0.000 | 0.000 | 0.000 | 30.000 | 30.000 | 5.197 | 11.246 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 8 | 1 | 123.578 | 0.000 | 19.000 | 19.000 | True |
| 2 | 1 | 2 | 5 | 215.046 | 0.000 | 30.000 | 30.000 | True |

## Physical Drone Routes
- physical_drone_1: 2 -> 4 -> 9 -> 11 -> 8 -> 6 -> 7 -> 12 -> 13 -> 2

