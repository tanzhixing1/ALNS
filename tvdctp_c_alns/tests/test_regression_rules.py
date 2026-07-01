from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pytest

from alns_solver import run_c_alns
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import (
    check_solution_feasible,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_peak_payload,
)
from initial_solution import initial_solution
from objective import objective


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
