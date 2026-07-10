from __future__ import annotations

import copy
from typing import Callable, List, Tuple

import pytest

import operators
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from operators import InsertionMove


CaseBuilder = Callable[[], Tuple[object, object, object, List[int], dict, bool]]


def _fixture(num_vans: int = 2, drones_per_van: int = 1):
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={3: num_vans, 4: num_vans},
        drones_per_van=drones_per_van,
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
    warehouse = int(state.selected_transshipment)
    vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == warehouse
    ][:num_vans]
    target = int(data.customers[0])
    remaining = [int(customer) for customer in data.customers if int(customer) != target]
    state.drone_sorties = []
    state.van_routes = {
        vans[0]: [warehouse, *remaining, warehouse],
        **{van_id: [warehouse, warehouse] for van_id in vans[1:]},
    }
    state.service_mode = {int(customer): "van" for customer in data.customers}
    state.service_mode[target] = "unassigned"
    state.unassigned = [target]
    state.sync_primary_van_route()
    for assignment in state.order_assignment.values():
        assignment["assigned_transshipment"] = warehouse
    for route in state.container_routes.values():
        route["destination_warehouse"] = warehouse
    return config, data, state, vans, target, warehouse


def _candidate(
    state,
    vans: List[str],
    warehouse: int,
    customers: List[int],
    *,
    launch_van: str | None = None,
    recovery_van: str | None = None,
    launch_position: int = 0,
    recovery_position: int = 0,
    drone_id: str | None = None,
) -> dict:
    launch_van = launch_van or vans[0]
    recovery_van = recovery_van or launch_van
    launch_route = state.van_routes[launch_van]
    recovery_route = state.van_routes[recovery_van]
    if drone_id is None:
        drone_id = next(
            drone
            for drone, carrier in state.drone_initial_carrier.items()
            if carrier == launch_van
        )
    return {
        "launch": int(launch_route[launch_position]),
        "customers": [int(customer) for customer in customers],
        "recovery": int(recovery_route[recovery_position]),
        "launch_van_id": launch_van,
        "recovery_van_id": recovery_van,
        "launch_position": int(launch_position),
        "recovery_position": int(recovery_position),
        "drone_id": drone_id,
    }


def _transfer_case(relaunch_from_old_van: bool = False):
    config, data, state, vans, target, warehouse = _fixture()
    transfer_node, existing_customer = [int(customer) for customer in data.customers[1:3]]
    state.van_routes[vans[0]] = [
        node for node in state.van_routes[vans[0]]
        if node not in {transfer_node, existing_customer}
    ]
    state.van_routes[vans[1]] = [warehouse, transfer_node, warehouse]
    state.service_mode[existing_customer] = "drone"
    state.service_mode[transfer_node] = "van"
    state.sync_primary_van_route()
    drone_id = next(
        drone for drone, carrier in state.drone_initial_carrier.items()
        if carrier == vans[0]
    )
    state.drone_sorties = [{
        "launch": warehouse,
        "customers": [existing_customer],
        "recovery": transfer_node,
        "launch_van_id": vans[0],
        "recovery_van_id": vans[1],
        "launch_position": 0,
        "recovery_position": 1,
        "drone_id": drone_id,
    }]
    launch_van = vans[0] if relaunch_from_old_van else vans[1]
    sortie = _candidate(
        state,
        vans,
        warehouse,
        [target],
        launch_van=launch_van,
        recovery_van=vans[1],
        launch_position=0 if relaunch_from_old_van else 1,
        recovery_position=1,
        drone_id=drone_id,
    )
    return config, data, state, [target], sortie, not relaunch_from_old_van


def _case_same_van():
    config, data, state, vans, target, warehouse = _fixture()
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), True


def _case_cross_van():
    config, data, state, vans, target, warehouse = _fixture()
    return config, data, state, [target], _candidate(
        state, vans, warehouse, [target], recovery_van=vans[1]
    ), True


def _case_cross_van_position_numbers_are_independent():
    config, data, state, vans, target, warehouse = _fixture()
    launch_position = 1
    return config, data, state, [target], _candidate(
        state,
        vans,
        warehouse,
        [target],
        launch_van=vans[0],
        recovery_van=vans[1],
        launch_position=launch_position,
        recovery_position=0,
    ), True


def _case_multi_customer():
    config, data, state, vans, target, warehouse = _fixture()
    second = int(data.customers[1])
    state.van_routes[vans[0]].remove(second)
    state.service_mode[second] = "unassigned"
    state.unassigned.append(second)
    state.sync_primary_van_route()
    return config, data, state, [target, second], _candidate(
        state, vans, warehouse, [target, second]
    ), True


def _case_wrong_carrier():
    config, data, state, vans, target, warehouse = _fixture()
    return config, data, state, [target], _candidate(
        state, vans, warehouse, [target], drone_id=next(
            drone for drone, carrier in state.drone_initial_carrier.items()
            if carrier == vans[1]
        )
    ), False


def _case_bad_launch_position():
    config, data, state, vans, target, warehouse = _fixture()
    sortie = _candidate(state, vans, warehouse, [target], launch_position=0)
    sortie["launch_position"] = 1
    return config, data, state, [target], sortie, False


def _case_bad_recovery_position():
    config, data, state, vans, target, warehouse = _fixture()
    state.van_routes[vans[1]] = [warehouse, int(data.customers[1]), warehouse]
    state.sync_primary_van_route()
    sortie = _candidate(
        state, vans, warehouse, [target], recovery_van=vans[1], recovery_position=0
    )
    sortie["recovery_position"] = 1
    return config, data, state, [target], sortie, False


def _case_reverse_same_van():
    config, data, state, vans, target, warehouse = _fixture()
    state.van_routes[vans[0]] = [warehouse, int(data.customers[1]), warehouse]
    state.sync_primary_van_route()
    return config, data, state, [target], _candidate(
        state, vans, warehouse, [target], launch_position=1, recovery_position=0
    ), False


def _case_terminal_launch():
    config, data, state, vans, target, warehouse = _fixture()
    state.van_routes[vans[0]] = [warehouse, warehouse]
    state.sync_primary_van_route()
    return config, data, state, [target], _candidate(
        state, vans, warehouse, [target], launch_position=1, recovery_position=0
    ), False


def _case_duplicate_customer():
    config, data, state, vans, target, warehouse = _fixture()
    return config, data, state, [target, target], _candidate(
        state, vans, warehouse, [target, target]
    ), False


def _case_already_served():
    config, data, state, vans, target, warehouse = _fixture()
    state.van_routes[vans[0]].insert(1, target)
    state.service_mode[target] = "van"
    state.unassigned = []
    state.sync_primary_van_route()
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_ineligible():
    config, data, state, vans, target, warehouse = _fixture()
    data.drone_eligible[target] = False
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_payload():
    config, data, state, vans, target, warehouse = _fixture()
    data.demands[target] = config.fleet.drone_capacity_kg + 1.0
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_endurance():
    config, data, state, vans, target, warehouse = _fixture()
    data.drone_distance_matrix[warehouse, target] = 100.0
    data.drone_distance_matrix[target, warehouse] = 100.0
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_energy():
    config, data, state, vans, target, warehouse = _fixture()
    config.fleet.drone_battery_capacity_kwh = 0.01
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_time_window():
    config, data, state, vans, target, warehouse = _fixture()
    ready = float(state.container_routes[0]["unload_complete"])
    data.time_windows[target] = (0.0, ready - 1.0)
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_container_ready():
    config, data, state, vans, target, warehouse = _fixture()
    state.container_routes[0]["unload_complete"] = 100_000.0
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_wrong_warehouse():
    config, data, state, vans, target, warehouse = _fixture()
    other_warehouse = next(
        node for node in state.transshipment_nodes if int(node) != warehouse
    )
    state.order_assignment[target]["assigned_transshipment"] = int(other_warehouse)
    state.container_routes[0]["destination_warehouse"] = int(other_warehouse)
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_downstream_window():
    config, data, state, vans, target, warehouse = _fixture()
    downstream = int(data.customers[1])
    data.time_windows[downstream] = (0.0, 0.0)
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), False


def _case_warehouse_relaunch():
    config, data, state, vans, target, warehouse = _fixture()
    existing_customer = int(data.customers[1])
    state.van_routes[vans[0]].remove(existing_customer)
    state.service_mode[existing_customer] = "drone"
    drone_id = next(
        drone for drone, carrier in state.drone_initial_carrier.items()
        if carrier == vans[0]
    )
    state.drone_sorties = [{
        "launch": warehouse,
        "customers": [existing_customer],
        "recovery": warehouse,
        "launch_van_id": vans[0],
        "recovery_van_id": vans[0],
        "launch_position": 0,
        "recovery_position": 0,
        "drone_id": drone_id,
    }]
    state.sync_primary_van_route()
    return config, data, state, [target], _candidate(
        state, vans, warehouse, [target], drone_id=drone_id
    ), False


def _case_dynamic_capacity():
    config, data, state, vans, target, warehouse = _fixture(num_vans=3)
    config.fleet.max_drones_carried_per_van = 2
    recovery_node = int(data.customers[1])
    existing_customer = int(data.customers[2])
    state.van_routes[vans[0]] = [
        warehouse,
        recovery_node,
        *[
            node for node in state.van_routes[vans[0]][1:-1]
            if node not in {recovery_node, existing_customer}
        ],
        warehouse,
    ]
    state.service_mode[existing_customer] = "drone"
    first_drone = next(
        drone for drone, carrier in state.drone_initial_carrier.items()
        if carrier == vans[1]
    )
    second_drone = next(
        drone for drone, carrier in state.drone_initial_carrier.items()
        if carrier == vans[2]
    )
    state.drone_sorties = [{
        "launch": warehouse,
        "customers": [existing_customer],
        "recovery": recovery_node,
        "launch_van_id": vans[1],
        "recovery_van_id": vans[0],
        "launch_position": 0,
        "recovery_position": 1,
        "drone_id": first_drone,
    }]
    state.sync_primary_van_route()
    return config, data, state, [target], _candidate(
        state,
        vans,
        warehouse,
        [target],
        launch_van=vans[2],
        recovery_van=vans[0],
        recovery_position=1,
        drone_id=second_drone,
    ), False


CASES: List[Tuple[str, CaseBuilder]] = [
    ("same_van", _case_same_van),
    ("cross_van", _case_cross_van),
    ("cross_van_position_numbers_are_independent", _case_cross_van_position_numbers_are_independent),
    ("multi_customer", _case_multi_customer),
    ("high_floor_drone", lambda: _high_floor_case()),
    ("physical_transfer_and_relaunch", lambda: _transfer_case(False)),
    ("relaunch_from_old_van", lambda: _transfer_case(True)),
    ("wrong_physical_carrier", _case_wrong_carrier),
    ("bad_launch_position", _case_bad_launch_position),
    ("bad_recovery_position", _case_bad_recovery_position),
    ("reverse_same_van", _case_reverse_same_van),
    ("terminal_launch", _case_terminal_launch),
    ("duplicate_customer", _case_duplicate_customer),
    ("already_served", _case_already_served),
    ("ineligible", _case_ineligible),
    ("payload", _case_payload),
    ("endurance", _case_endurance),
    ("energy", _case_energy),
    ("time_window", _case_time_window),
    ("container_ready", _case_container_ready),
    ("wrong_container_warehouse", _case_wrong_warehouse),
    ("downstream_time_window", _case_downstream_window),
    ("warehouse_relaunch", _case_warehouse_relaunch),
    ("dynamic_capacity", _case_dynamic_capacity),
]


def _high_floor_case():
    config, data, state, vans, target, warehouse = _fixture()
    data.is_high_floor[target] = True
    return config, data, state, [target], _candidate(state, vans, warehouse, [target]), True


@pytest.mark.parametrize("name,builder", CASES, ids=[name for name, _ in CASES])
def test_stage2a_local_drone_checker_differential(name: str, builder: CaseBuilder) -> None:
    config, data, state, customers, sortie, expected_local = builder()
    local = operators._drone_insert_hard_feasible(
        customers, sortie, state, data, config
    )
    assert local is expected_local, f"{name}: local feasibility mismatch"

    candidate_state = state.copy()
    operators._apply_move(
        candidate_state,
        int(customers[0]),
        InsertionMove(mode="drone", cost=0.0, sortie=copy.deepcopy(sortie)),
    )
    full_ok, full_violations = check_solution_feasible(
        candidate_state, data, config
    )
    if expected_local:
        if name == "cross_van_position_numbers_are_independent":
            assert not full_ok
            assert full_violations == [
                "drone_id drone_0 has launch_position 1 after recovery_position 0."
            ], f"{name}: unexpected Category C violations: {full_violations}"
        else:
            assert full_ok, f"{name}: local true but full checker failed: {full_violations}"
    elif name != "bad_launch_position":
        assert not full_ok, f"{name}: local false but full checker accepted candidate"
    else:
        # The full checker intentionally resolves an invalid position hint by node.
        assert full_ok, f"{name}: representation fallback changed: {full_violations}"
