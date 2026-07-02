from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pytest

from alns_solver import run_c_alns
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import (
    check_solution_feasible,
    compute_timing,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_peak_payload,
)
from initial_solution import initial_solution
from objective import objective
from operators import _best_drone_move, consolidate_drone_sorties
from evaluation import _active_plot_van_routes, evaluate_and_save


@dataclass(frozen=True)
class Case:
    name: str
    num_orders: int
    num_transshipments: int
    num_containers: int
    iterations: int


CASES = [
    Case("tiny", num_orders=6, num_transshipments=2, num_containers=1, iterations=80),
    Case("small", num_orders=10, num_transshipments=2, num_containers=1, iterations=80),
    Case("medium", num_orders=20, num_transshipments=3, num_containers=2, iterations=50),
]


def _solve(case: Case):
    config = build_config(
        num_customers=case.num_orders,
        num_orders=case.num_orders,
        num_transshipments=case.num_transshipments,
        num_containers=case.num_containers,
        iterations=case.iterations,
        seed=42,
    )
    # Keep the regression fixtures focused on model-rule consistency instead
    # of resource stress; the default toy fleet has only three drones.
    config.data.high_floor_ratio = 0.15
    data = generate_toy_data(config)
    result = run_c_alns(data, config)
    total_cost, breakdown = objective(result.best_state, data, config)
    feasible, violations = check_solution_feasible(result.best_state, data, config)
    return config, data, result.best_state, total_cost, breakdown, feasible, violations


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_regression_model_rules_across_scales(case: Case) -> None:
    config, data, state, total_cost, breakdown, feasible, violations = _solve(case)

    assert feasible is True, violations
    assert state.unassigned == []

    served = state.get_van_customers() + state.get_drone_customers()
    service_counts = Counter(served)
    assert set(served) == set(data.customers)
    assert all(service_counts[customer] == 1 for customer in data.customers)

    timing = state.timing
    assert timing.get("time_window_violations", []) == []
    assert total_cost > 0

    objective_without_waiting = (
        breakdown["truck_cost"]
        + breakdown["van_cost"]
        + breakdown["drone_cost"]
        + breakdown["penalty_cost"]
    )
    assert breakdown["total_cost"] == pytest.approx(objective_without_waiting)
    assert total_cost == pytest.approx(objective_without_waiting)
    waiting_cost = breakdown.get("waiting_cost_reported", 0.0)
    if waiting_cost:
        assert total_cost != pytest.approx(objective_without_waiting + waiting_cost)

    physical_routes = timing.get("drone_physical_routes", {})
    sortie_drone_ids = {
        str(sortie["drone_id"])
        for sortie in state.drone_sorties
        if isinstance(sortie, dict) and sortie.get("drone_id") is not None
    }
    assert breakdown["used_drones"] == len(physical_routes)
    assert breakdown["used_drones"] == len(sortie_drone_ids)
    assert breakdown["used_drone_sorties"] == len(state.drone_sorties)

    for count in timing.get("drone_warehouse_launch_count", {}).values():
        assert int(count) <= 1
    for count in timing.get("drone_warehouse_return_count", {}).values():
        assert int(count) <= 1

    for sortie in state.drone_sorties:
        assert drone_sortie_energy(sortie, data, config) <= (
            config.fleet.drone_battery_capacity_kwh + 1e-9
        )
        assert drone_sortie_peak_payload(sortie, data, config) <= (
            config.fleet.drone_capacity_kg + 1e-9
        )
        assert drone_sortie_distance(sortie, data) <= (
            config.fleet.drone_endurance_km + 1e-9
        )


def test_tiny_multi_van_resource_model() -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=40,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.15
    data = generate_toy_data(config)
    result = run_c_alns(data, config)
    total_cost, breakdown = objective(result.best_state, data, config)
    feasible, violations = check_solution_feasible(result.best_state, data, config)

    assert config.fleet.drones_per_van == 2
    for warehouse, vans in config.warehouse_num_vans(data.transshipment_nodes).items():
        assert config.warehouse_num_drones(data.transshipment_nodes)[warehouse] == (
            vans * config.fleet.drones_per_van
        )

    assert feasible is True, violations
    assert result.best_state.unassigned == []

    served = result.best_state.get_van_customers() + result.best_state.get_drone_customers()
    service_counts = Counter(served)
    assert set(served) == set(data.customers)
    assert all(service_counts[customer] == 1 for customer in data.customers)

    assert breakdown["used_vans"] <= config.total_num_vans(data.transshipment_nodes)
    assert breakdown["used_drones"] <= config.total_num_drones(data.transshipment_nodes)

    carried_by_van = Counter(result.best_state.drone_initial_carrier.values())
    assert all(count <= config.fleet.drones_per_van for count in carried_by_van.values())

    assert breakdown["used_drone_sorties"] == len(result.best_state.drone_sorties)
    used_drone_ids = {
        str(sortie["drone_id"])
        for sortie in result.best_state.drone_sorties
        if isinstance(sortie, dict) and sortie.get("drone_id")
    }
    assert breakdown["used_drones"] == len(used_drone_ids)

    objective_without_waiting = (
        breakdown["truck_cost"]
        + breakdown["van_cost"]
        + breakdown["drone_cost"]
        + breakdown["penalty_cost"]
    )
    assert breakdown["total_cost"] == pytest.approx(objective_without_waiting)
    assert total_cost == pytest.approx(objective_without_waiting)


def test_initial_solution_does_not_balance_into_second_van_when_one_van_is_feasible() -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drones_per_van=2,
        drone_enabled=False,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    total_cost, breakdown = objective(state, data, config)
    feasible, violations = check_solution_feasible(state, data, config)

    assert feasible is True, violations
    assert state.unassigned == []
    assert breakdown["used_vans"] == 1
    active_customer_routes = [
        route for route in state.van_routes.values() if any(node in data.customers for node in route)
    ]
    assert len(active_customer_routes) == 1
    assert total_cost == pytest.approx(breakdown["total_cost"])


def _manual_cross_van_docking_state(data, config, recovery_route_has_node: bool):
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    assert len(selected_vans) >= 2
    launch_van, recovery_van = selected_vans[:2]
    drone_id = next(
        drone_id
        for drone_id, carrier in state.drone_initial_carrier.items()
        if carrier == launch_van
    )
    recovery_node = data.customers[0]
    drone_customer = data.customers[1]
    remaining_customers = [
        customer
        for customer in data.customers
        if customer not in {recovery_node, drone_customer}
    ]

    if recovery_route_has_node:
        state.van_routes = {
            launch_van: [selected, *remaining_customers, selected],
            recovery_van: [selected, recovery_node, selected],
        }
    else:
        state.van_routes = {
            launch_van: [selected, recovery_node, *remaining_customers, selected],
            recovery_van: [selected, selected],
        }
    state.sync_primary_van_route()

    state.drone_sorties = [
        {
            "launch": selected,
            "customers": [drone_customer],
            "recovery": recovery_node,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": False,
            "drone_id": drone_id,
            "launch_van_id": launch_van,
            "recovery_van_id": recovery_van,
            "launch_position": 0,
            "recovery_position": 1,
        }
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[drone_customer] = "drone"
    state.unassigned = []
    return state, launch_van, recovery_van, recovery_node


def test_manual_cross_van_flexible_docking_feasible_when_recovery_van_visits_node() -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    state, launch_van, recovery_van, recovery_node = _manual_cross_van_docking_state(
        data, config, recovery_route_has_node=True
    )

    feasible, violations = check_solution_feasible(state, data, config)
    total_cost, breakdown = objective(state, data, config)

    assert launch_van != recovery_van
    assert feasible is True, violations
    assert recovery_node in state.van_routes[recovery_van]
    assert recovery_node in state.timing["van_arrival_by_van"][recovery_van]
    assert breakdown["used_vans"] == 2
    assert breakdown["used_drone_sorties"] == 1
    assert total_cost == pytest.approx(breakdown["total_cost"])


def test_manual_cross_van_flexible_docking_infeasible_when_recovery_van_misses_node() -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    state, launch_van, recovery_van, recovery_node = _manual_cross_van_docking_state(
        data, config, recovery_route_has_node=False
    )

    feasible, violations = check_solution_feasible(state, data, config)

    assert launch_van != recovery_van
    assert recovery_node not in state.van_routes[recovery_van]
    assert feasible is False
    assert any("drone launch/recovery not on van_route" in item for item in violations)


def _cross_van_timing_fixture(num_drone_customers: int = 1):
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    data.drone_eligible = {customer: True for customer in data.customers}
    for customer in data.customers:
        data.demands[customer] = 1.0
        data.pickup_demands[customer] = 0.0
        data.service_times[customer] = 0.0
        data.time_windows[customer] = (0.0, 10_000.0)

    state = initial_solution(data, config)
    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    launch_van, recovery_van = selected_vans[:2]
    recovery_node = data.customers[0]
    next_node = data.customers[1]
    drone_customers = data.customers[2 : 2 + num_drone_customers]
    drone_ids = [
        drone_id
        for drone_id, carrier in sorted(state.drone_initial_carrier.items())
        if carrier == launch_van
    ]
    assert len(drone_ids) >= num_drone_customers

    state.van_routes = {
        launch_van: [selected, selected],
        recovery_van: [selected, recovery_node, next_node, selected],
    }
    state.sync_primary_van_route()
    state.service_mode = {customer: "unassigned" for customer in data.customers}
    state.service_mode[recovery_node] = "van"
    state.service_mode[next_node] = "van"
    for customer in drone_customers:
        state.service_mode[customer] = "drone"
    state.unassigned = [
        customer
        for customer in data.customers
        if state.service_mode.get(customer) == "unassigned"
    ]
    state.drone_sorties = [
        {
            "launch": selected,
            "customers": [customer],
            "recovery": recovery_node,
            "launch_van_id": launch_van,
            "recovery_van_id": recovery_van,
            "launch_position": 0,
            "recovery_position": 1,
            "drone_id": drone_ids[idx],
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": False,
        }
        for idx, customer in enumerate(drone_customers)
    ]
    return config, data, state, launch_van, recovery_van, recovery_node, next_node, drone_customers


def _set_symmetric_distance(matrix, first: int, second: int, distance: float) -> None:
    matrix[first, second] = float(distance)
    matrix[second, first] = float(distance)


def test_cross_van_recovery_waiting_propagates() -> None:
    config, data, state, launch_van, recovery_van, recovery_node, next_node, drone_customers = (
        _cross_van_timing_fixture()
    )
    selected = state.selected_transshipment
    drone_customer = drone_customers[0]
    _set_symmetric_distance(data.ground_distance_matrix, selected, recovery_node, 4.0)
    _set_symmetric_distance(data.ground_distance_matrix, recovery_node, next_node, 10.0)
    _set_symmetric_distance(data.drone_distance_matrix, selected, drone_customer, 20.0)
    _set_symmetric_distance(data.drone_distance_matrix, drone_customer, recovery_node, 20.0)

    timing = compute_timing(state, data, config)
    sortie = state.drone_sorties[0]
    recovery_time = float(sortie["recovery_time"])
    recovery_sequence = timing["van_arrival_sequence_by_van"][recovery_van]
    next_arrival = float(recovery_sequence[2]["arrival_time"])
    travel_after_recovery = data.ground_distance_matrix[recovery_node, next_node] / config.fleet.van_speed_kmph * 60.0

    assert launch_van != recovery_van
    assert float(sortie["drone_arrival_time"]) > float(recovery_sequence[1]["arrival_time"])
    assert next_arrival + 1e-9 >= recovery_time + travel_after_recovery


def test_cross_van_recovery_van_late() -> None:
    config, data, state, launch_van, recovery_van, recovery_node, next_node, drone_customers = (
        _cross_van_timing_fixture()
    )
    selected = state.selected_transshipment
    drone_customer = drone_customers[0]
    _set_symmetric_distance(data.ground_distance_matrix, selected, recovery_node, 20.0)
    _set_symmetric_distance(data.ground_distance_matrix, recovery_node, next_node, 5.0)
    _set_symmetric_distance(data.drone_distance_matrix, selected, drone_customer, 1.0)
    _set_symmetric_distance(data.drone_distance_matrix, drone_customer, recovery_node, 1.0)

    timing = compute_timing(state, data, config)
    sortie = state.drone_sorties[0]
    recovery_van_arrival = float(timing["van_arrival_sequence_by_van"][recovery_van][1]["arrival_time"])

    assert launch_van != recovery_van
    assert float(sortie["recovery_time"]) == pytest.approx(recovery_van_arrival)
    assert float(sortie["drone_arrival_time"]) < recovery_van_arrival
    assert float(sortie["drone_waiting_time"]) > 0.0


def test_multiple_recoveries_same_position() -> None:
    config, data, state, _, recovery_van, recovery_node, next_node, drone_customers = (
        _cross_van_timing_fixture(num_drone_customers=2)
    )
    selected = state.selected_transshipment
    _set_symmetric_distance(data.ground_distance_matrix, selected, recovery_node, 4.0)
    _set_symmetric_distance(data.ground_distance_matrix, recovery_node, next_node, 10.0)
    _set_symmetric_distance(data.drone_distance_matrix, selected, drone_customers[0], 6.0)
    _set_symmetric_distance(data.drone_distance_matrix, drone_customers[0], recovery_node, 6.0)
    _set_symmetric_distance(data.drone_distance_matrix, selected, drone_customers[1], 18.0)
    _set_symmetric_distance(data.drone_distance_matrix, drone_customers[1], recovery_node, 18.0)

    timing = compute_timing(state, data, config)
    recovery_sequence = timing["van_arrival_sequence_by_van"][recovery_van]
    latest_recovery_time = max(float(sortie["recovery_time"]) for sortie in state.drone_sorties)
    travel_after_recovery = data.ground_distance_matrix[recovery_node, next_node] / config.fleet.van_speed_kmph * 60.0

    assert {int(sortie["recovery_position"]) for sortie in state.drone_sorties} == {1}
    assert float(recovery_sequence[1]["departure_time"]) == pytest.approx(latest_recovery_time)
    assert float(recovery_sequence[2]["arrival_time"]) + 1e-9 >= (
        latest_recovery_time + travel_after_recovery
    )


def test_best_drone_move_can_generate_cross_van_recovery() -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    launch_van, recovery_van = selected_vans[:2]
    recovery_node = data.customers[0]
    drone_customer = data.customers[1]
    remaining = [
        customer
        for customer in data.customers
        if customer not in {recovery_node, drone_customer}
    ]
    state.van_routes = {
        launch_van: [selected, *remaining, selected],
        recovery_van: [selected, recovery_node, selected],
    }
    state.sync_primary_van_route()
    state.drone_sorties = []
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[drone_customer] = "unassigned"
    state.unassigned = [drone_customer]

    data.drone_distance_matrix[selected, drone_customer] = 1.0
    data.drone_distance_matrix[drone_customer, recovery_node] = 1.0
    data.drone_distance_matrix[drone_customer, selected] = 100.0
    data.drone_distance_matrix[recovery_node, drone_customer] = 100.0

    move = _best_drone_move(drone_customer, state, data, config)

    assert move is not None
    assert move.sortie is not None
    assert move.sortie["launch_van_id"] == launch_van
    assert move.sortie["recovery_van_id"] == recovery_van


def test_route_plan_detail_outputs_flexible_docking_fields(tmp_path) -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=5,
        seed=42,
        output_dir=str(tmp_path),
    )
    config.data.high_floor_ratio = 0.15
    data = generate_toy_data(config)
    result = run_c_alns(data, config)
    evaluate_and_save(result, data, config)

    detail = (tmp_path / "route_plan_detail.txt").read_text(encoding="utf-8")
    assert "launch_van_id" in detail
    assert "recovery_van_id" in detail
    assert "same_van_recovery" in detail
    assert "cross_van_recovery" in detail
    assert "number_of_same_van_sorties" in detail
    assert "number_of_cross_van_sorties" in detail
    assert "number_of_multi_customer_sorties" in detail


def test_routes_plot_active_van_filter_excludes_inactive_empty_van() -> None:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drone_enabled=False,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    active_van, inactive_van = selected_vans[:2]
    state.van_routes = {
        active_van: [selected, data.customers[0], selected],
        inactive_van: [selected, selected],
    }
    state.drone_sorties = []
    state.service_mode = {customer: "unassigned" for customer in data.customers}
    state.service_mode[data.customers[0]] = "van"
    state.unassigned = data.customers[1:].copy()
    state.sync_primary_van_route()

    active_routes = _active_plot_van_routes(state, data)

    assert active_van in active_routes
    assert inactive_van not in active_routes


def test_drone_sortie_consolidation_merges_feasible_same_anchor_sorties() -> None:
    config = build_config(
        num_customers=3,
        num_orders=3,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={2: 2, 3: 2},
        drone_enabled=False,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    data.drone_eligible = {customer: True for customer in data.customers}
    for customer in data.customers:
        data.demands[customer] = 1.0
        data.pickup_demands[customer] = 0.0
        data.time_windows[customer] = (0.0, 10_000.0)
        data.service_times[customer] = 0.0

    state = initial_solution(data, config)
    config.fleet.drone_enabled = True
    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    van_id = selected_vans[0]
    drone_id = next(
        drone_id
        for drone_id, carrier in state.drone_initial_carrier.items()
        if carrier == van_id
    )
    anchor, first_drone_customer, second_drone_customer = data.customers
    state.van_routes = {van_id: [selected, anchor, selected]}
    state.sync_primary_van_route()
    state.drone_sorties = [
        {
            "launch": anchor,
            "customers": [first_drone_customer],
            "recovery": anchor,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": True,
            "drone_id": drone_id,
            "launch_van_id": van_id,
            "recovery_van_id": van_id,
            "launch_position": 1,
            "recovery_position": 1,
        },
        {
            "launch": anchor,
            "customers": [second_drone_customer],
            "recovery": anchor,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": True,
            "drone_id": drone_id,
            "launch_van_id": van_id,
            "recovery_van_id": van_id,
            "launch_position": 1,
            "recovery_position": 1,
        },
    ]
    state.service_mode = {
        anchor: "van",
        first_drone_customer: "drone",
        second_drone_customer: "drone",
    }
    state.unassigned = []

    before_cost, before_breakdown = objective(state, data, config)
    before_sorties = before_breakdown["used_drone_sorties"]
    consolidated = consolidate_drone_sorties(state, data, config)
    after_cost, after_breakdown = objective(consolidated, data, config)
    feasible, violations = check_solution_feasible(consolidated, data, config)
    served = consolidated.get_van_customers() + consolidated.get_drone_customers()
    service_counts = Counter(served)

    assert feasible is True, violations
    assert after_breakdown["used_drone_sorties"] <= before_sorties
    assert len(consolidated.drone_sorties) == 1
    assert all(service_counts[customer] == 1 for customer in data.customers)
    assert after_cost <= before_cost + 1e-9
