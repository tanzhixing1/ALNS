# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 2 -> 13 -> 11 -> 9 -> 7 -> 8 -> 10 -> 3 |
| used_drones | 1 |
| used_drone_sorties | 2 |
| total_cost | 571.478 |
| waiting_cost_reported | 4.444 |
| drone_energy_kwh | 10.578 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | transshipment | 76.870 | 104.000 | 0.000 | 104.000 | 0.000 | 0.000 | 0.000 | 0.000 | 104.000 | 0.000 | 104.000 | True |
| 1 | 13 | customer | 85.510 | 104.000 | 0.000 | 104.000 | 7.000 | 2.000 | 21.000 | 0.000 | 76.000 | 2.000 | 78.000 | True |
| 2 | 11 | customer | 117.385 | 76.000 | 2.000 | 78.000 | 3.000 | 6.000 | 0.000 | 7.000 | 73.000 | 15.000 | 88.000 | True |
| 3 | 9 | customer | 146.825 | 73.000 | 15.000 | 88.000 | 7.000 | 4.000 | 0.000 | 0.000 | 66.000 | 19.000 | 85.000 | True |
| 4 | 7 | customer | 187.469 | 66.000 | 19.000 | 85.000 | 18.000 | 3.000 | 0.000 | 0.000 | 48.000 | 22.000 | 70.000 | True |
| 5 | 8 | customer | 219.420 | 48.000 | 22.000 | 70.000 | 5.000 | 2.000 | 25.000 | 0.000 | 18.000 | 24.000 | 42.000 | True |
| 6 | 10 | customer | 239.507 | 18.000 | 24.000 | 42.000 | 18.000 | 6.000 | 0.000 | 7.000 | 0.000 | 37.000 | 37.000 | True |
| 7 | 3 | transshipment | 253.817 | 0.000 | 37.000 | 37.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 37.000 | 37.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | launch | 13 |  | 1 | 85.510 | 21.000 | 0.000 | 21.000 | 0.000 | 0.000 | 21.000 | 0.000 | 21.000 | 0.000 | 0.000 | True | True |
| 1 | 1 | serve_customer | 12 | 13->12 |  | 105.506 | 21.000 | 0.000 | 21.000 | 1.000 | 6.000 | 20.000 | 6.000 | 26.000 | 4.393 | 4.393 | True | True |
| 1 | 1 | serve_customer | 5 | 12->5 |  | 108.726 | 20.000 | 6.000 | 26.000 | 20.000 | 1.000 | 0.000 | 7.000 | 7.000 | 0.841 | 5.234 | True | True |
| 1 | 1 | recovery | 11 | 5->11 | 2 | 121.861 | 0.000 | 7.000 | 7.000 | 0.000 | 0.000 | 0.000 | 7.000 | 7.000 | 1.353 | 6.587 | True | True |
| 2 | 1 | launch | 8 |  | 5 | 219.420 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | True | True |
| 2 | 1 | serve_customer | 14 | 8->14 |  | 228.085 | 25.000 | 0.000 | 25.000 | 14.000 | 1.000 | 11.000 | 1.000 | 12.000 | 2.192 | 2.192 | True | True |
| 2 | 1 | serve_customer | 6 | 14->6 |  | 237.152 | 11.000 | 1.000 | 12.000 | 11.000 | 6.000 | 0.000 | 7.000 | 7.000 | 1.312 | 3.504 | True | True |
| 2 | 1 | recovery | 10 | 6->10 | 6 | 241.885 | 0.000 | 7.000 | 7.000 | 0.000 | 0.000 | 0.000 | 7.000 | 7.000 | 0.487 | 3.991 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 11 | 2 | 121.861 | 0.000 | 7.000 | 7.000 | True |
| 2 | 1 | 10 | 6 | 241.885 | 0.000 | 7.000 | 7.000 | True |

## Physical Drone Routes
- physical_drone_1: 2 -> 13 -> 12 -> 5 -> 11 -> 8 -> 14 -> 6 -> 10 -> 3

