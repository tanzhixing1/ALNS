# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 3 -> 7 -> 5 -> 12 -> 3 |
| used_drones | 2 |
| used_drone_sorties | 5 |
| total_cost | 811.953 |
| waiting_cost_reported | 187.719 |
| drone_energy_kwh | 18.928 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3 | warehouse | 106.349 | 117.000 | 0.000 | 117.000 | 0.000 | 0.000 | 1.000 | 0.000 | 116.000 | 0.000 | 116.000 | True |
| 1 | 7 | customer | 150.539 | 116.000 | 0.000 | 116.000 | 14.000 | 7.000 | 20.000 | 0.000 | 82.000 | 7.000 | 89.000 | True |
| 2 | 5 | customer | 225.039 | 82.000 | 7.000 | 89.000 | 3.000 | 15.000 | 47.000 | 38.000 | 32.000 | 60.000 | 92.000 | True |
| 3 | 12 | customer | 303.835 | 32.000 | 60.000 | 92.000 | 18.000 | 3.000 | 14.000 | 25.000 | 0.000 | 88.000 | 88.000 | True |
| 4 | 3 | warehouse | 326.896 | 0.000 | 88.000 | 88.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 88.000 | 88.000 | True |
| 0 | 3 | warehouse | 106.349 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |
| 1 | 3 | warehouse | 106.349 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_1 | launch | 7 |  | 1 | 150.539 | 20.000 | 0.000 | 20.000 | 0.000 | 0.000 | 20.000 | 0.000 | 20.000 | 0.000 | 0.000 | True | True |
| 1 | drone_1 | serve_customer | 10 | 7->10 |  | 159.605 | 20.000 | 0.000 | 20.000 | 20.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.916 | 1.916 | True | True |
| 1 | drone_1 | recovery | 7 | 10->7 | 1 | 168.670 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.405 | 2.321 | True | True |
| 2 | drone_1 | launch | 5 |  | 2 | 225.039 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | True | True |
| 2 | drone_1 | serve_customer | 11 | 5->11 |  | 238.383 | 25.000 | 0.000 | 25.000 | 9.000 | 11.000 | 16.000 | 11.000 | 27.000 | 3.376 | 3.376 | True | True |
| 2 | drone_1 | serve_customer | 14 | 11->14 |  | 247.037 | 16.000 | 11.000 | 27.000 | 16.000 | 14.000 | 0.000 | 25.000 | 25.000 | 2.334 | 5.710 | True | True |
| 2 | drone_1 | recovery | 5 | 14->5 | 2 | 253.631 | 0.000 | 25.000 | 25.000 | 0.000 | 0.000 | 0.000 | 25.000 | 25.000 | 1.668 | 7.378 | True | True |
| 3 | drone_1 | launch | 5 |  | 2 | 253.631 | 22.000 | 0.000 | 22.000 | 0.000 | 0.000 | 22.000 | 0.000 | 22.000 | 0.000 | 0.000 | True | True |
| 3 | drone_1 | serve_customer | 8 | 5->8 |  | 265.095 | 22.000 | 0.000 | 22.000 | 7.000 | 9.000 | 15.000 | 9.000 | 24.000 | 2.614 | 2.614 | True | True |
| 3 | drone_1 | serve_customer | 6 | 8->6 |  | 269.390 | 15.000 | 9.000 | 24.000 | 15.000 | 4.000 | 0.000 | 13.000 | 13.000 | 1.051 | 3.665 | True | True |
| 3 | drone_1 | recovery | 5 | 6->5 | 2 | 278.346 | 0.000 | 13.000 | 13.000 | 0.000 | 0.000 | 0.000 | 13.000 | 13.000 | 1.370 | 5.035 | True | True |
| 4 | drone_0 | launch | 12 |  | 3 | 303.835 | 14.000 | 0.000 | 14.000 | 0.000 | 0.000 | 14.000 | 0.000 | 14.000 | 0.000 | 0.000 | True | True |
| 4 | drone_0 | serve_customer | 13 | 12->13 |  | 310.310 | 14.000 | 0.000 | 14.000 | 14.000 | 15.000 | 0.000 | 15.000 | 15.000 | 1.045 | 1.045 | True | True |
| 4 | drone_0 | recovery | 12 | 13->12 | 3 | 316.786 | 0.000 | 15.000 | 15.000 | 0.000 | 0.000 | 0.000 | 15.000 | 15.000 | 1.099 | 2.144 | True | True |
| 5 | drone_0 | launch | 3 |  | 0 | 106.349 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | True | True |
| 5 | drone_0 | serve_customer | 9 | 3->9 |  | 114.722 | 1.000 | 0.000 | 1.000 | 1.000 | 10.000 | 0.000 | 10.000 | 10.000 | 0.444 | 0.444 | True | True |
| 5 | drone_0 | recovery | 12 | 9->12 | 3 | 303.835 | 0.000 | 10.000 | 10.000 | 0.000 | 0.000 | 0.000 | 10.000 | 10.000 | 1.607 | 2.051 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_1 | 7 | 1 | 168.670 | 0.000 | 0.000 | 0.000 | True |
| 2 | drone_1 | 5 | 2 | 253.631 | 0.000 | 25.000 | 25.000 | True |
| 3 | drone_1 | 5 | 2 | 278.346 | 0.000 | 13.000 | 13.000 | True |
| 4 | drone_0 | 12 | 3 | 316.786 | 0.000 | 15.000 | 15.000 | True |
| 5 | drone_0 | 12 | 3 | 303.835 | 0.000 | 10.000 | 10.000 | True |

## Physical Drone Routes
- physical_drone_0: 3 -> 9 -> 12 -> 13 -> 12
- physical_drone_1: 3 -> 7 -> 10 -> 7 -> 5 -> 11 -> 14 -> 5 -> 8 -> 6 -> 5

