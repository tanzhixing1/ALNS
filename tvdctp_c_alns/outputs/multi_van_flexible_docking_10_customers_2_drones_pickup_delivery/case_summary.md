# Multi-van flexible docking case, 10 customers, 2 drones, pickup and delivery

customers: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
selected_transshipment: 2
launch_van_id: van_0
recovery_van_id: van_1
launch_van_route: [2, 9, 10, 2]
recovery_van_route: [2, 4, 5, 6, 11, 12, 13, 2]
timing_scheduler: fixed-point
timing_iterations: 3
feasible: True
total_cost: 830.925

customer demands:
- customer 4: delivery=2.000, pickup=1.000, mode=van
- customer 5: delivery=3.000, pickup=2.000, mode=van
- customer 6: delivery=4.000, pickup=1.000, mode=van
- customer 7: delivery=2.000, pickup=2.000, mode=drone
- customer 8: delivery=3.000, pickup=1.000, mode=drone
- customer 9: delivery=4.000, pickup=2.000, mode=van
- customer 10: delivery=2.000, pickup=1.000, mode=van
- customer 11: delivery=3.000, pickup=2.000, mode=van
- customer 12: delivery=4.000, pickup=1.000, mode=van
- customer 13: delivery=2.000, pickup=2.000, mode=van

drone sorties:
- sortie 1: {'launch': 2, 'customers': [7], 'recovery': 4, 'launch_van_id': 'van_0', 'recovery_van_id': 'van_1', 'launch_position': 0, 'recovery_position': 1, 'drone_id': 'drone_0', 'launch_time': 76.87038609479045, 'recovery_time': 103.87038609479045, 'van_waiting_time': 21.0, 'drone_waiting_time': 0.0, 'same_node': False, 'drone_arrival_time': 103.87038609479045, 'synchronized_recovery_time': 103.87038609479045}
  recovery_van_arrival_at_recovery=82.870
  drone_arrival_at_recovery=103.870
  synchronized_recovery_time=103.870
  recovery_van_departure_at_recovery=103.870
  next_node_after_recovery=5
  next_node_arrival_after_wait_propagation=111.370
  van_waiting_time=21.000
  drone_waiting_time=0.000
- sortie 2: {'launch': 2, 'customers': [8], 'recovery': 5, 'launch_van_id': 'van_0', 'recovery_van_id': 'van_1', 'launch_position': 0, 'recovery_position': 2, 'drone_id': 'drone_1', 'launch_time': 76.87038609479045, 'recovery_time': 111.37038609479045, 'van_waiting_time': 0.0, 'drone_waiting_time': 1.5, 'same_node': False, 'drone_arrival_time': 109.87038609479045, 'synchronized_recovery_time': 111.37038609479045}
  recovery_van_arrival_at_recovery=111.370
  drone_arrival_at_recovery=109.870
  synchronized_recovery_time=111.370
  recovery_van_departure_at_recovery=111.370
  next_node_after_recovery=6
  next_node_arrival_after_wait_propagation=123.370
  van_waiting_time=0.000
  drone_waiting_time=1.500

Generated files:
- D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\multi_van_flexible_docking_10_customers_2_drones_pickup_delivery\route_plan_detail.txt
- D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\multi_van_flexible_docking_10_customers_2_drones_pickup_delivery\route_plan_detail.csv
- D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\multi_van_flexible_docking_10_customers_2_drones_pickup_delivery\routes.png
- D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\multi_van_flexible_docking_10_customers_2_drones_pickup_delivery\load_timeline.md
- D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\multi_van_flexible_docking_10_customers_2_drones_pickup_delivery\route_load_timeline.png
- D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\multi_van_flexible_docking_10_customers_2_drones_pickup_delivery\summary.txt