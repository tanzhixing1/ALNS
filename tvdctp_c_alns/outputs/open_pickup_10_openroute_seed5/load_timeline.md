# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 2 -> 5 -> 13 -> 3 |
| used_drones | 2 |
| used_drone_sorties | 4 |
| total_cost | 673.561 |
| waiting_cost_reported | 37.759 |
| drone_energy_kwh | 31.731 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | transshipment | 76.870 | 104.000 | 0.000 | 104.000 | 0.000 | 0.000 | 35.000 | 0.000 | 69.000 | 0.000 | 69.000 | True |
| 1 | 5 | customer | 87.441 | 69.000 | 0.000 | 69.000 | 11.000 | 18.000 | 44.000 | 42.000 | 14.000 | 60.000 | 74.000 | True |
| 2 | 13 | customer | 153.773 | 14.000 | 60.000 | 74.000 | 14.000 | 0.000 | 0.000 | 22.000 | 0.000 | 82.000 | 82.000 | True |
| 3 | 3 | transshipment | 175.217 | 0.000 | 82.000 | 82.000 | 0.000 | 0.000 | 0.000 | 20.000 | 0.000 | 102.000 | 102.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | launch | 5 |  | 1 | 135.638 | 21.000 | 0.000 | 21.000 | 0.000 | 0.000 | 21.000 | 0.000 | 21.000 | 0.000 | 0.000 | True | True |
| 1 | 1 | serve_customer | 4 | 5->4 |  | 155.239 | 21.000 | 0.000 | 21.000 | 20.000 | 2.000 | 1.000 | 2.000 | 3.000 | 4.306 | 4.306 | True | True |
| 1 | 1 | serve_customer | 11 | 4->11 |  | 158.458 | 1.000 | 2.000 | 3.000 | 1.000 | 18.000 | 0.000 | 20.000 | 20.000 | 0.224 | 4.530 | True | True |
| 1 | 1 | recovery | 3 | 11->3 | 3 | 178.911 | 0.000 | 20.000 | 20.000 | 0.000 | 0.000 | 0.000 | 20.000 | 20.000 | 4.322 | 8.852 | True | True |
| 2 | 2 | launch | 5 |  | 1 | 135.638 | 23.000 | 0.000 | 23.000 | 0.000 | 0.000 | 23.000 | 0.000 | 23.000 | 0.000 | 0.000 | True | True |
| 2 | 2 | serve_customer | 7 | 5->7 |  | 144.292 | 23.000 | 0.000 | 23.000 | 5.000 | 4.000 | 18.000 | 4.000 | 22.000 | 2.045 | 2.045 | True | True |
| 2 | 2 | serve_customer | 9 | 7->9 |  | 154.335 | 18.000 | 4.000 | 22.000 | 18.000 | 18.000 | 0.000 | 22.000 | 22.000 | 2.290 | 4.335 | True | True |
| 2 | 2 | recovery | 13 | 9->13 | 2 | 160.121 | 0.000 | 22.000 | 22.000 | 0.000 | 0.000 | 0.000 | 22.000 | 22.000 | 1.319 | 5.654 | True | True |
| 3 | 1 | launch | 2 |  | 0 | 76.870 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | True | True |
| 3 | 1 | serve_customer | 6 | 2->6 |  | 87.152 | 25.000 | 0.000 | 25.000 | 18.000 | 7.000 | 7.000 | 7.000 | 14.000 | 2.601 | 2.601 | True | True |
| 3 | 1 | serve_customer | 12 | 6->12 |  | 98.652 | 7.000 | 7.000 | 14.000 | 7.000 | 6.000 | 0.000 | 13.000 | 13.000 | 1.855 | 4.457 | True | True |
| 3 | 1 | recovery | 5 | 12->5 | 1 | 106.556 | 0.000 | 13.000 | 13.000 | 0.000 | 0.000 | 0.000 | 13.000 | 13.000 | 1.209 | 5.666 | True | True |
| 4 | 2 | launch | 2 |  | 0 | 76.870 | 10.000 | 0.000 | 10.000 | 0.000 | 0.000 | 10.000 | 0.000 | 10.000 | 0.000 | 0.000 | True | True |
| 4 | 2 | serve_customer | 8 | 2->8 |  | 100.292 | 10.000 | 0.000 | 10.000 | 7.000 | 11.000 | 3.000 | 11.000 | 14.000 | 2.998 | 2.998 | True | True |
| 4 | 2 | serve_customer | 10 | 8->10 |  | 112.774 | 3.000 | 11.000 | 14.000 | 3.000 | 18.000 | 0.000 | 29.000 | 29.000 | 2.014 | 5.012 | True | True |
| 4 | 2 | recovery | 5 | 10->5 | 1 | 135.638 | 0.000 | 29.000 | 29.000 | 0.000 | 0.000 | 0.000 | 29.000 | 29.000 | 6.547 | 11.559 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 3 | 3 | 178.911 | 0.000 | 20.000 | 20.000 | True |
| 2 | 2 | 13 | 2 | 160.121 | 0.000 | 22.000 | 22.000 | True |
| 3 | 1 | 5 | 1 | 106.556 | 0.000 | 13.000 | 13.000 | True |
| 4 | 2 | 5 | 1 | 135.638 | 0.000 | 29.000 | 29.000 | True |

## Physical Drone Routes
- physical_drone_1: 2 -> 6 -> 12 -> 5 -> 4 -> 11 -> 3
- physical_drone_2: 2 -> 8 -> 10 -> 5 -> 7 -> 9 -> 13 -> 3

