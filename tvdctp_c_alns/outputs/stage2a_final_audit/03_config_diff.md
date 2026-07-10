# Config Diff: reconstructed previous vs current

Previous objective `1484.491724` is reproduced by `high_floor_ratio=0.35`; current regression profile uses `0.15`. Other fields are held equal in this audit reconstruction.

| Field | Previous | Current | Same/Different | Affects initial objective? |
| --- | --- | --- | --- | --- |
| `alns.collect_full_candidate_diagnostics` | `True` | `True` | Same | No / diagnostic only |
| `alns.collect_local_feasibility_cache_stats` | `False` | `False` | Same | No / diagnostic only |
| `alns.cooling_rate` | `0.9995` | `0.9995` | Same | No / diagnostic only |
| `alns.customer_removal_ratio` | `0.2` | `0.2` | Same | No / diagnostic only |
| `alns.early_stop_enabled` | `True` | `True` | Same | No / diagnostic only |
| `alns.enable_local_feasibility_cache` | `False` | `False` | Same | No / diagnostic only |
| `alns.enable_shadow_prefilter` | `False` | `False` | Same | No / diagnostic only |
| `alns.initial_temperature` | `1000.0` | `1000.0` | Same | No / diagnostic only |
| `alns.max_iterations` | `10` | `10` | Same | No / diagnostic only |
| `alns.max_no_improve` | `100` | `100` | Same | No / diagnostic only |
| `alns.max_no_improvement` | `100` | `100` | Same | No / diagnostic only |
| `alns.random_seed` | `42` | `42` | Same | No / diagnostic only |
| `alns.reaction_coefficient` | `0.2` | `0.2` | Same | No / diagnostic only |
| `alns.scores` | `[5.0, 3.0, 1.0, 0.0]` | `[5.0, 3.0, 1.0, 0.0]` | Same | No / diagnostic only |
| `alns.weight_update_interval` | `50` | `50` | Same | No / diagnostic only |
| `config_builder_path` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\config.py` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\config.py` | Same | No / diagnostic only |
| `cost.drone_cost_per_km` | `0.052` | `0.052` | Same | No / diagnostic only |
| `cost.drone_fixed_cost` | `169.0` | `169.0` | Same | No / diagnostic only |
| `cost.infeasible_penalty` | `10000.0` | `10000.0` | Same | No / diagnostic only |
| `cost.time_penalty_per_hour` | `38.9` | `38.9` | Same | No / diagnostic only |
| `cost.tractor_cost_per_km` | `1.93` | `1.93` | Same | No / diagnostic only |
| `cost.tractor_fixed_cost` | `166.0` | `166.0` | Same | No / diagnostic only |
| `cost.trailer_fixed_cost` | `0.0` | `0.0` | Same | No / diagnostic only |
| `cost.van_cost_per_km` | `0.875` | `0.875` | Same | No / diagnostic only |
| `cost.van_fixed_cost` | `59.0` | `59.0` | Same | No / diagnostic only |
| `data.container_origin` | `port` | `port` | Same | No / diagnostic only |
| `data.high_floor_ratio` | `0.35` | `0.15` | Different | Yes |
| `data.max_demand_kg` | `20` | `20` | Same | No / diagnostic only |
| `data.max_pickup_demand_kg` | `20` | `20` | Same | No / diagnostic only |
| `data.min_demand_kg` | `0` | `0` | Same | No / diagnostic only |
| `data.min_pickup_demand_kg` | `0` | `0` | Same | No / diagnostic only |
| `data.num_containers` | `2` | `2` | Same | No / diagnostic only |
| `data.num_customers` | `20` | `20` | Same | No / diagnostic only |
| `data.num_orders` | `20` | `20` | Same | No / diagnostic only |
| `data.num_transshipments` | `3` | `3` | Same | No / diagnostic only |
| `data.port_node` | `0` | `0` | Same | No / diagnostic only |
| `data.road_distance_factor` | `1.0` | `1.0` | Same | No / diagnostic only |
| `data.service_time_min` | `0.0` | `0.0` | Same | No / diagnostic only |
| `data.time_window_end_min` | `360.0` | `360.0` | Same | No / diagnostic only |
| `data.time_window_start_min` | `0.0` | `0.0` | Same | No / diagnostic only |
| `data.tractor_depot_node` | `None` | `None` | Same | No / diagnostic only |
| `data.trailer_depot_node` | `None` | `None` | Same | No / diagnostic only |
| `data.transshipment_start_node` | `3` | `3` | Same | No / diagnostic only |
| `data.truck_depot_node` | `1` | `1` | Same | No / diagnostic only |
| `data.vans_per_transshipment_by_scale.large` | `4` | `4` | Same | No / diagnostic only |
| `data.vans_per_transshipment_by_scale.medium` | `3` | `3` | Same | No / diagnostic only |
| `data.vans_per_transshipment_by_scale.small` | `2` | `2` | Same | No / diagnostic only |
| `data_generator_path` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\dataset_loader.py` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\dataset_loader.py` | Same | No / diagnostic only |
| `derived_warehouse_num_drones.3` | `6` | `6` | Same | No / diagnostic only |
| `derived_warehouse_num_drones.4` | `6` | `6` | Same | No / diagnostic only |
| `derived_warehouse_num_drones.5` | `6` | `6` | Same | No / diagnostic only |
| `derived_warehouse_num_vans.3` | `3` | `3` | Same | No / diagnostic only |
| `derived_warehouse_num_vans.4` | `3` | `3` | Same | No / diagnostic only |
| `derived_warehouse_num_vans.5` | `3` | `3` | Same | No / diagnostic only |
| `fixed_run_parameters.iterations` | `10` | `10` | Same | No / diagnostic only |
| `fixed_run_parameters.num_containers` | `2` | `2` | Same | No / diagnostic only |
| `fixed_run_parameters.num_customers` | `20` | `20` | Same | No / diagnostic only |
| `fixed_run_parameters.num_orders` | `20` | `20` | Same | No / diagnostic only |
| `fixed_run_parameters.num_transshipments` | `3` | `3` | Same | No / diagnostic only |
| `fixed_run_parameters.seed` | `42` | `42` | Same | No / diagnostic only |
| `fleet.container_load_time` | `0.0` | `0.0` | Same | No / diagnostic only |
| `fleet.container_unload_time` | `0.0` | `0.0` | Same | No / diagnostic only |
| `fleet.drone_base_energy_coeff` | `0.18` | `0.18` | Same | No / diagnostic only |
| `fleet.drone_battery_capacity_kwh` | `13.8` | `13.8` | Same | No / diagnostic only |
| `fleet.drone_capacity_kg` | `30.0` | `30.0` | Same | No / diagnostic only |
| `fleet.drone_enabled` | `True` | `True` | Same | No / diagnostic only |
| `fleet.drone_endurance_km` | `90.0` | `90.0` | Same | No / diagnostic only |
| `fleet.drone_payload_energy_coeff` | `0.5` | `0.5` | Same | No / diagnostic only |
| `fleet.drone_self_weight_kg` | `5.0` | `5.0` | Same | No / diagnostic only |
| `fleet.drone_speed_kmph` | `80.0` | `80.0` | Same | No / diagnostic only |
| `fleet.drones_per_van` | `2` | `2` | Same | No / diagnostic only |
| `fleet.max_drones_carried_per_van` | `3` | `3` | Same | No / diagnostic only |
| `fleet.num_tractors` | `1` | `1` | Same | No / diagnostic only |
| `fleet.num_trailers` | `1` | `1` | Same | No / diagnostic only |
| `fleet.num_trucks` | `1` | `1` | Same | No / diagnostic only |
| `fleet.tractor_speed_kmph` | `30.0` | `30.0` | Same | No / diagnostic only |
| `fleet.trailer_attach_time` | `0.0` | `0.0` | Same | No / diagnostic only |
| `fleet.trailer_detach_time` | `0.0` | `0.0` | Same | No / diagnostic only |
| `fleet.van_capacity_kg` | `500.0` | `500.0` | Same | No / diagnostic only |
| `fleet.van_speed_kmph` | `40.0` | `40.0` | Same | No / diagnostic only |
| `objective_note` | `previous 1484.491724 profile value is reproduced with default high_floor_ratio=0.35` | `current initial objective is produced by the regression fixture's explicit high_floor_ratio=0.15` | Different | No / diagnostic only |
| `operator_registry.candidate_search_space_changed` | `False` | `False` | Same | No / diagnostic only |
| `operator_registry.destroy_registry` | `['cascade_aware_removal', 'drone_task_removal', 'greedy_removal', 'random_customer_removal', 'related_customer_removal', 'route_segment_removal', 'switch_transshipment_operator']` | `['cascade_aware_removal', 'drone_task_removal', 'greedy_removal', 'random_customer_removal', 'related_customer_removal', 'route_segment_removal', 'switch_transshipment_operator']` | Same | No / diagnostic only |
| `operator_registry.extended_mode` | `True` | `True` | Same | No / diagnostic only |
| `operator_registry.operator_semantics_changed` | `False` | `False` | Same | No / diagnostic only |
| `operator_registry.paper_destroy_registry` | `['random_customer_removal', 'greedy_removal', 'related_customer_removal', 'cascade_aware_removal']` | `['random_customer_removal', 'greedy_removal', 'related_customer_removal', 'cascade_aware_removal']` | Same | No / diagnostic only |
| `operator_registry.paper_mode` | `False` | `False` | Same | No / diagnostic only |
| `operator_registry.paper_repair_registry` | `['best_mode_repair', 'greedy_van_repair', 'regret_repair', 'cascade_repair']` | `['best_mode_repair', 'greedy_van_repair', 'regret_repair', 'cascade_repair']` | Same | No / diagnostic only |
| `operator_registry.repair_registry` | `['best_mode_repair', 'cascade_repair', 'greedy_drone_repair', 'greedy_van_repair', 'regret_repair']` | `['best_mode_repair', 'cascade_repair', 'greedy_drone_repair', 'greedy_van_repair', 'regret_repair']` | Same | No / diagnostic only |
| `output_dir` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\stage2a_final_audit` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\outputs\stage2a_final_audit` | Same | No / diagnostic only |
| `profile_entry` | `run_c_alns` | `run_c_alns` | Same | No / diagnostic only |
| `profile_script_path` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\alns_solver.py` | `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns\alns_solver.py` | Same | No / diagnostic only |
| `source` | `reconstructed from config.py default high_floor_ratio=0.35; objective reproduction check` | `tests/test_regression_rules.py::_solve equivalent fixed medium fixture; high_floor_ratio explicitly set to 0.15` | Different | No / diagnostic only |
