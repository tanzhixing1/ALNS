# Multi-van flexible docking case, 10 customers, pickup and delivery

customers: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
selected_transshipment: 2
launch_van_id: van_0
recovery_van_id: van_1
launch_van_route: [2, 7, 8, 9, 2]
recovery_van_route: [2, 4, 5, 10, 11, 12, 13, 2]
drone_sortie: {'launch': 2, 'customers': [6], 'recovery': 4, 'launch_van_id': 'van_0', 'recovery_van_id': 'van_1', 'launch_position': 0, 'recovery_position': 1, 'drone_id': 'drone_0', 'launch_time': 76.87038609479045, 'recovery_time': 106.87038609479045, 'van_waiting_time': 24.0, 'drone_waiting_time': 0.0, 'same_node': False, 'drone_arrival_time': 106.87038609479045, 'synchronized_recovery_time': 106.87038609479045}

customer_demands:
- customer 4: delivery=2.000, pickup=1.000, mode=van
- customer 5: delivery=3.000, pickup=2.000, mode=van
- customer 6: delivery=4.000, pickup=1.000, mode=drone
- customer 7: delivery=2.000, pickup=2.000, mode=van
- customer 8: delivery=3.000, pickup=1.000, mode=van
- customer 9: delivery=4.000, pickup=2.000, mode=van
- customer 10: delivery=2.000, pickup=1.000, mode=van
- customer 11: delivery=3.000, pickup=2.000, mode=van
- customer 12: delivery=4.000, pickup=1.000, mode=van
- customer 13: delivery=2.000, pickup=2.000, mode=van

drone_customer_delivery: 4.000
drone_customer_pickup: 1.000
timing_scheduler: fixed-point
timing_iterations: 2
recovery_van_arrival_at_recovery: 82.870
drone_arrival_at_recovery: 106.870
synchronized_recovery_time: 106.870
recovery_van_departure_at_recovery: 106.870
next_node_after_recovery: 5
next_node_arrival_after_wait_propagation: 121.870
van_waiting_time: 24.000
drone_waiting_time: 0.000
feasible: True
total_cost: 689.153