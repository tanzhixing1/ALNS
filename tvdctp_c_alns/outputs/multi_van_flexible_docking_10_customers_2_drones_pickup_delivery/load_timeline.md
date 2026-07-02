# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 2 -> 9 -> 10 -> 2 |
| used_drones | 2 |
| used_drone_sorties | 2 |
| total_cost | 830.925 |
| waiting_cost_reported | 14.587 |
| drone_energy_kwh | 3.680 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | transshipment | 76.870 | 11.000 | 0.000 | 11.000 | 0.000 | 0.000 | 5.000 | 0.000 | 6.000 | 0.000 | 6.000 | True |
| 1 | 9 | customer | 100.883 | 6.000 | 0.000 | 6.000 | 4.000 | 2.000 | 0.000 | 0.000 | 2.000 | 2.000 | 4.000 | True |
| 2 | 10 | customer | 144.132 | 2.000 | 2.000 | 4.000 | 2.000 | 1.000 | 0.000 | 0.000 | 0.000 | 3.000 | 3.000 | True |
| 3 | 2 | transshipment | 164.233 | 0.000 | 3.000 | 3.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 3.000 | 3.000 | True |
| 0 | 2 | transshipment | 76.870 | 18.000 | 0.000 | 18.000 | 0.000 | 0.000 | 0.000 | 0.000 | 18.000 | 0.000 | 18.000 | True |
| 1 | 4 | customer | 82.870 | 18.000 | 0.000 | 18.000 | 2.000 | 1.000 | 0.000 | 2.000 | 16.000 | 3.000 | 19.000 | True |
| 2 | 5 | customer | 111.370 | 16.000 | 3.000 | 19.000 | 3.000 | 2.000 | 0.000 | 1.000 | 13.000 | 6.000 | 19.000 | True |
| 3 | 6 | customer | 123.370 | 13.000 | 6.000 | 19.000 | 4.000 | 1.000 | 0.000 | 0.000 | 9.000 | 7.000 | 16.000 | True |
| 4 | 11 | customer | 168.662 | 9.000 | 7.000 | 16.000 | 3.000 | 2.000 | 0.000 | 0.000 | 6.000 | 9.000 | 15.000 | True |
| 5 | 12 | customer | 201.870 | 6.000 | 9.000 | 15.000 | 4.000 | 1.000 | 0.000 | 0.000 | 2.000 | 10.000 | 12.000 | True |
| 6 | 13 | customer | 219.394 | 2.000 | 10.000 | 12.000 | 2.000 | 2.000 | 0.000 | 0.000 | 0.000 | 12.000 | 12.000 | True |
| 7 | 2 | transshipment | 234.368 | 0.000 | 12.000 | 12.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 12.000 | 12.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_0 | launch | 2 |  | 0 | 76.870 | 2.000 | 0.000 | 2.000 | 0.000 | 0.000 | 2.000 | 0.000 | 2.000 | 0.000 | 0.000 | True | True |
| 1 | drone_0 | serve_customer | 7 | 2->7 |  | 90.370 | 2.000 | 0.000 | 2.000 | 2.000 | 2.000 | 0.000 | 2.000 | 2.000 | 0.828 | 0.828 | True | True |
| 1 | drone_0 | recovery | 4 | 7->4 | 1 | 103.870 | 0.000 | 2.000 | 2.000 | 0.000 | 0.000 | 0.000 | 2.000 | 2.000 | 0.828 | 1.656 | True | True |
| 2 | drone_1 | launch | 2 |  | 0 | 76.870 | 3.000 | 0.000 | 3.000 | 0.000 | 0.000 | 3.000 | 0.000 | 3.000 | 0.000 | 0.000 | True | True |
| 2 | drone_1 | serve_customer | 8 | 2->8 |  | 93.370 | 3.000 | 0.000 | 3.000 | 3.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.149 | 1.149 | True | True |
| 2 | drone_1 | recovery | 5 | 8->5 | 2 | 111.370 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.875 | 2.024 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_0 | 4 | 1 | 103.870 | 0.000 | 2.000 | 2.000 | True |
| 2 | drone_1 | 5 | 2 | 111.370 | 0.000 | 1.000 | 1.000 | True |

## Physical Drone Routes
- physical_drone_0: 2 -> 7 -> 4
- physical_drone_1: 2 -> 8 -> 5

