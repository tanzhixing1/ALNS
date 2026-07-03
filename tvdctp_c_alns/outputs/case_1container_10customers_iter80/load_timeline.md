# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 3 -> 9 -> 12 -> 5 -> 3 |
| used_drones | 2 |
| used_drone_sorties | 5 |
| total_cost | 789.343 |
| waiting_cost_reported | 88.249 |
| drone_energy_kwh | 22.990 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3 | warehouse | 106.349 | 117.000 | 0.000 | 117.000 | 0.000 | 0.000 | 0.000 | 0.000 | 117.000 | 0.000 | 117.000 | True |
| 1 | 9 | customer | 123.095 | 117.000 | 0.000 | 117.000 | 1.000 | 10.000 | 34.000 | 7.000 | 82.000 | 17.000 | 99.000 | True |
| 2 | 12 | customer | 183.327 | 82.000 | 17.000 | 99.000 | 18.000 | 3.000 | 14.000 | 15.000 | 50.000 | 35.000 | 85.000 | True |
| 3 | 5 | customer | 221.767 | 50.000 | 35.000 | 85.000 | 3.000 | 15.000 | 47.000 | 38.000 | 0.000 | 88.000 | 88.000 | True |
| 4 | 3 | warehouse | 276.750 | 0.000 | 88.000 | 88.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 88.000 | 88.000 | True |
| 0 | 3 | warehouse | 106.349 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |
| 1 | 3 | warehouse | 106.349 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_1 | launch | 9 |  | 1 | 123.095 | 20.000 | 0.000 | 20.000 | 0.000 | 0.000 | 20.000 | 0.000 | 20.000 | 0.000 | 0.000 | True | True |
| 1 | drone_1 | serve_customer | 10 | 9->10 |  | 140.656 | 20.000 | 0.000 | 20.000 | 20.000 | 0.000 | 0.000 | 0.000 | 0.000 | 3.711 | 3.711 | True | True |
| 1 | drone_1 | recovery | 9 | 10->9 | 1 | 158.217 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.784 | 4.496 | True | True |
| 2 | drone_0 | launch | 5 |  | 3 | 221.767 | 22.000 | 0.000 | 22.000 | 0.000 | 0.000 | 22.000 | 0.000 | 22.000 | 0.000 | 0.000 | True | True |
| 2 | drone_0 | serve_customer | 6 | 5->6 |  | 230.723 | 22.000 | 0.000 | 22.000 | 15.000 | 4.000 | 7.000 | 4.000 | 11.000 | 2.042 | 2.042 | True | True |
| 2 | drone_0 | serve_customer | 8 | 6->8 |  | 235.018 | 7.000 | 4.000 | 11.000 | 7.000 | 9.000 | 0.000 | 13.000 | 13.000 | 0.586 | 2.628 | True | True |
| 2 | drone_0 | recovery | 5 | 8->5 | 3 | 246.482 | 0.000 | 13.000 | 13.000 | 0.000 | 0.000 | 0.000 | 13.000 | 13.000 | 1.754 | 4.382 | True | True |
| 3 | drone_1 | launch | 5 |  | 3 | 221.767 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | 25.000 | 0.000 | 25.000 | 0.000 | 0.000 | True | True |
| 3 | drone_1 | serve_customer | 11 | 5->11 |  | 235.112 | 25.000 | 0.000 | 25.000 | 9.000 | 11.000 | 16.000 | 11.000 | 27.000 | 3.376 | 3.376 | True | True |
| 3 | drone_1 | serve_customer | 14 | 11->14 |  | 243.765 | 16.000 | 11.000 | 27.000 | 16.000 | 14.000 | 0.000 | 25.000 | 25.000 | 2.334 | 5.710 | True | True |
| 3 | drone_1 | recovery | 5 | 14->5 | 3 | 250.359 | 0.000 | 25.000 | 25.000 | 0.000 | 0.000 | 0.000 | 25.000 | 25.000 | 1.668 | 7.378 | True | True |
| 4 | drone_0 | launch | 12 |  | 2 | 183.327 | 14.000 | 0.000 | 14.000 | 0.000 | 0.000 | 14.000 | 0.000 | 14.000 | 0.000 | 0.000 | True | True |
| 4 | drone_0 | serve_customer | 13 | 12->13 |  | 189.803 | 14.000 | 0.000 | 14.000 | 14.000 | 15.000 | 0.000 | 15.000 | 15.000 | 1.045 | 1.045 | True | True |
| 4 | drone_0 | recovery | 12 | 13->12 | 2 | 196.278 | 0.000 | 15.000 | 15.000 | 0.000 | 0.000 | 0.000 | 15.000 | 15.000 | 1.099 | 2.144 | True | True |
| 5 | drone_0 | launch | 9 |  | 1 | 123.095 | 14.000 | 0.000 | 14.000 | 0.000 | 0.000 | 14.000 | 0.000 | 14.000 | 0.000 | 0.000 | True | True |
| 5 | drone_0 | serve_customer | 7 | 9->7 |  | 140.462 | 14.000 | 0.000 | 14.000 | 14.000 | 7.000 | 0.000 | 7.000 | 7.000 | 2.802 | 2.802 | True | True |
| 5 | drone_0 | recovery | 9 | 7->9 | 1 | 157.830 | 0.000 | 7.000 | 7.000 | 0.000 | 0.000 | 0.000 | 7.000 | 7.000 | 1.789 | 4.591 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_1 | 9 | 1 | 158.217 | 0.000 | 0.000 | 0.000 | True |
| 2 | drone_0 | 5 | 3 | 246.482 | 0.000 | 13.000 | 13.000 | True |
| 3 | drone_1 | 5 | 3 | 250.359 | 0.000 | 25.000 | 25.000 | True |
| 4 | drone_0 | 12 | 2 | 196.278 | 0.000 | 15.000 | 15.000 | True |
| 5 | drone_0 | 9 | 1 | 157.830 | 0.000 | 7.000 | 7.000 | True |

## Physical Drone Routes
- physical_drone_0: 3 -> 9 -> 7 -> 9 -> 12 -> 13 -> 12 -> 5 -> 6 -> 8 -> 5
- physical_drone_1: 3 -> 9 -> 10 -> 9 -> 5 -> 11 -> 14 -> 5

