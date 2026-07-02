# TVDCTP-T Load Timeline

All times are minutes. Loads are kilograms.
D = delivery load, P = pickup load, T = total payload.

## Summary
| field | value |
| --- | --- |
| feasible | True |
| van_route | 2 -> 7 -> 8 -> 9 -> 2 |
| used_drones | 1 |
| used_drone_sorties | 1 |
| total_cost | 689.153 |
| waiting_cost_reported | 15.560 |
| drone_energy_kwh | 1.965 |

## Van Load Timeline
| position | node | node_type | time | delivery_before | pickup_before | payload_before | van_delivered | van_picked_up | drone_delivery_launched | drone_pickup_recovered | delivery_after | pickup_after | payload_after | capacity_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | transshipment | 76.870 | 13.000 | 0.000 | 13.000 | 0.000 | 0.000 | 4.000 | 0.000 | 9.000 | 0.000 | 9.000 | True |
| 1 | 7 | customer | 99.388 | 9.000 | 0.000 | 9.000 | 2.000 | 2.000 | 0.000 | 0.000 | 7.000 | 2.000 | 9.000 | True |
| 2 | 8 | customer | 125.788 | 7.000 | 2.000 | 9.000 | 3.000 | 1.000 | 0.000 | 0.000 | 4.000 | 3.000 | 7.000 | True |
| 3 | 9 | customer | 160.054 | 4.000 | 3.000 | 7.000 | 4.000 | 2.000 | 0.000 | 0.000 | 0.000 | 5.000 | 5.000 | True |
| 4 | 2 | transshipment | 184.066 | 0.000 | 5.000 | 5.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 5.000 | 5.000 | True |
| 0 | 2 | transshipment | 76.870 | 16.000 | 0.000 | 16.000 | 0.000 | 0.000 | 0.000 | 0.000 | 16.000 | 0.000 | 16.000 | True |
| 1 | 4 | customer | 82.870 | 16.000 | 0.000 | 16.000 | 2.000 | 1.000 | 0.000 | 1.000 | 14.000 | 2.000 | 16.000 | True |
| 2 | 5 | customer | 121.870 | 14.000 | 2.000 | 16.000 | 3.000 | 2.000 | 0.000 | 0.000 | 11.000 | 4.000 | 15.000 | True |
| 3 | 10 | customer | 156.287 | 11.000 | 4.000 | 15.000 | 2.000 | 1.000 | 0.000 | 0.000 | 9.000 | 5.000 | 14.000 | True |
| 4 | 11 | customer | 202.072 | 9.000 | 5.000 | 14.000 | 3.000 | 2.000 | 0.000 | 0.000 | 6.000 | 7.000 | 13.000 | True |
| 5 | 12 | customer | 235.279 | 6.000 | 7.000 | 13.000 | 4.000 | 1.000 | 0.000 | 0.000 | 2.000 | 8.000 | 10.000 | True |
| 6 | 13 | customer | 252.803 | 2.000 | 8.000 | 10.000 | 2.000 | 2.000 | 0.000 | 0.000 | 0.000 | 10.000 | 10.000 | True |
| 7 | 2 | transshipment | 267.777 | 0.000 | 10.000 | 10.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 10.000 | 10.000 | True |

## Drone Load Timeline
| sortie_id | drone_id | event | node | route_leg | van_position | time | delivery_before | pickup_before | payload_before | delivered | picked_up | delivery_after | pickup_after | payload_after | energy_increment | cumulative_energy | capacity_feasible | battery_feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_0 | launch | 2 |  | 0 | 76.870 | 4.000 | 0.000 | 4.000 | 0.000 | 0.000 | 4.000 | 0.000 | 4.000 | 0.000 | 0.000 | True | True |
| 1 | drone_0 | serve_customer | 6 | 2->6 |  | 91.870 | 4.000 | 0.000 | 4.000 | 4.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.170 | 1.170 | True | True |
| 1 | drone_0 | recovery | 4 | 6->4 | 1 | 106.870 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.795 | 1.965 | True | True |

## Drone Recovery Load Summary
| sortie_id | drone_id | recovery_node | recovery_position | recovery_time | recovery_delivery_load | recovery_pickup_load | recovery_total_payload | transferred_to_van |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | drone_0 | 4 | 1 | 106.870 | 0.000 | 1.000 | 1.000 | True |

## Physical Drone Routes
- physical_drone_0: 2 -> 6 -> 4

