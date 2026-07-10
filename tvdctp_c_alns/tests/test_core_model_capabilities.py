from __future__ import annotations

from collections import Counter

from alns_solver import run_c_alns
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from objective import objective


def _prepare_customers(data) -> None:
    data.is_high_floor = {customer: False for customer in data.customers}
    data.drone_eligible = {customer: True for customer in data.customers}
    for customer in data.customers:
        data.demands[customer] = 1.0
        data.pickup_demands[customer] = 0.0
        data.service_times[customer] = 0.0
        data.time_windows[customer] = (0.0, 10_000.0)


def _multi_van_base_state():
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={3: 2, 4: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    _prepare_customers(data)
    state = initial_solution(data, config)
    selected = int(state.selected_transshipment)
    launch_van, recovery_van = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == selected
    ][:2]
    drone_id = next(
        drone_id
        for drone_id, carrier in state.drone_initial_carrier.items()
        if carrier == launch_van
    )
    extra_recovery_drone = next(
        drone_id
        for drone_id, carrier in state.drone_initial_carrier.items()
        if carrier == recovery_van
    )
    state.drone_initial_carrier.pop(extra_recovery_drone)
    state.drone_home_warehouse.pop(extra_recovery_drone, None)
    recovery_node, drone_customer, *van_customers = data.customers
    state.van_routes = {
        launch_van: [selected, *van_customers, selected],
        recovery_van: [selected, recovery_node, selected],
    }
    state.drone_sorties = [
        {
            "launch": selected,
            "customers": [drone_customer],
            "recovery": recovery_node,
            "launch_van_id": launch_van,
            "recovery_van_id": recovery_van,
            "launch_position": 0,
            "recovery_position": 1,
            "drone_id": drone_id,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": False,
        }
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[drone_customer] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()
    return config, data, state, launch_van, recovery_van, drone_id


def _check_case(state, data, config, expected):
    feasible, violations = check_solution_feasible(state, data, config)
    assert feasible is expected, violations
    if expected:
        assert violations == []
    return violations


def test_feasible_cross_van_docking() -> None:
    config, data, state, launch_van, recovery_van, _ = _multi_van_base_state()

    _check_case(state, data, config, True)
    assert launch_van != recovery_van
    assert state.drone_sorties[0]["recovery"] in state.van_routes[recovery_van]


def test_feasible_cross_van_then_relaunch_from_recovery_van() -> None:
    config, data, state, _, recovery_van, drone_id = _multi_van_base_state()
    recovery_node = data.customers[0]
    relaunch_customer = data.customers[-1]
    state.van_routes = {
        van_id: [node for node in route if node != relaunch_customer]
        for van_id, route in state.van_routes.items()
    }
    state.drone_sorties.append(
        {
            "launch": recovery_node,
            "customers": [relaunch_customer],
            "recovery": recovery_node,
            "launch_van_id": recovery_van,
            "recovery_van_id": recovery_van,
            "launch_position": 1,
            "recovery_position": 1,
            "drone_id": drone_id,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": True,
        }
    )
    state.service_mode[relaunch_customer] = "drone"
    state.sync_primary_van_route()

    _check_case(state, data, config, True)


def test_infeasible_relaunch_from_old_van_after_cross_recovery() -> None:
    config, data, state, launch_van, _, drone_id = _multi_van_base_state()
    relaunch_customer = data.customers[-1]
    launch_node = data.customers[2]
    state.van_routes = {
        van_id: [node for node in route if node != relaunch_customer]
        for van_id, route in state.van_routes.items()
    }
    state.drone_sorties.append(
        {
            "launch": launch_node,
            "customers": [relaunch_customer],
            "recovery": launch_node,
            "launch_van_id": launch_van,
            "recovery_van_id": launch_van,
            "launch_position": 1,
            "recovery_position": 1,
            "drone_id": drone_id,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
            "same_node": True,
        }
    )
    state.service_mode[relaunch_customer] = "drone"
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("before sortie but launches from" in item for item in violations)


def test_infeasible_recovery_before_launch_same_van() -> None:
    config, data, state, launch_van, _, drone_id = _multi_van_base_state()
    customer = data.customers[-1]
    state.van_routes = {launch_van: [state.selected_transshipment, data.customers[2], customer, state.selected_transshipment]}
    state.drone_sorties = [
        {
            "launch": customer,
            "customers": [data.customers[3]],
            "recovery": data.customers[2],
            "launch_van_id": launch_van,
            "recovery_van_id": launch_van,
            "launch_position": 2,
            "recovery_position": 1,
            "drone_id": drone_id,
        }
    ]
    state.service_mode = {node: "van" for node in data.customers}
    state.service_mode[data.customers[3]] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("recovery occurs before launch" in item for item in violations)


def test_infeasible_recovery_node_not_on_recovery_van_route() -> None:
    config, data, state, _, recovery_van, _ = _multi_van_base_state()
    missing_node = data.customers[2]
    state.drone_sorties[0]["recovery"] = missing_node
    state.drone_sorties[0]["recovery_position"] = 1
    assert missing_node not in state.van_routes[recovery_van]

    violations = _check_case(state, data, config, False)
    assert any("launch/recovery not on van_route" in item for item in violations)


def test_infeasible_drone_continues_after_warehouse_return() -> None:
    config, data, state, launch_van, _, drone_id = _multi_van_base_state()
    first_drone_customer = data.customers[3]
    second_drone_customer = data.customers[-1]
    van_customers = [
        customer
        for customer in data.customers
        if customer not in {first_drone_customer, second_drone_customer}
    ]
    state.van_routes = {
        launch_van: [state.selected_transshipment, *van_customers, state.selected_transshipment],
    }
    state.drone_sorties = [
        {
            "launch": state.selected_transshipment,
            "customers": [first_drone_customer],
            "recovery": state.selected_transshipment,
            "launch_van_id": launch_van,
            "recovery_van_id": launch_van,
            "launch_position": 0,
            "recovery_position": 0,
            "drone_id": drone_id,
        },
        {
            "launch": data.customers[2],
            "customers": [second_drone_customer],
            "recovery": data.customers[2],
            "launch_van_id": launch_van,
            "recovery_van_id": launch_van,
            "launch_position": 1,
            "recovery_position": 1,
            "drone_id": drone_id,
        },
    ]
    state.service_mode = {node: "van" for node in data.customers}
    state.service_mode[first_drone_customer] = "drone"
    state.service_mode[second_drone_customer] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("continues after recovery at warehouse" in item for item in violations)


def test_infeasible_exceed_van_drone_capacity() -> None:
    config, data, state, _, recovery_van, _ = _multi_van_base_state()
    removed_drone = next(
        drone_id
        for drone_id, carrier in config.build_drone_initial_carrier(data.transshipment_nodes).items()
        if carrier == recovery_van and drone_id not in state.drone_initial_carrier
    )
    state.drone_initial_carrier[removed_drone] = recovery_van
    state.drone_home_warehouse[removed_drone] = int(state.van_home[recovery_van])
    config.fleet.max_drones_carried_per_van = 2

    violations = _check_case(state, data, config, False)
    assert any("exceeding max_drones_carried_per_van" in item for item in violations)


def _two_container_state(*, different_destinations: bool = False, high_floor: bool = False):
    config = build_config(
        num_customers=8,
        num_orders=8,
        num_transshipments=2,
        num_containers=2,
        iterations=1,
        seed=42,
        warehouse_num_vans={3: 2, 4: 2},
        drones_per_van=2,
        num_tractors=2,
        num_trailers=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    _prepare_customers(data)
    if different_destinations:
        first, second = data.transshipment_nodes[:2]
        for container_id, warehouse in [(0, first), (1, second)]:
            other = second if warehouse == first else first
            for customer in data.container_assignment[container_id]["customers"]:
                data.ground_distance_matrix[warehouse, customer] = 1.0
                data.ground_distance_matrix[customer, warehouse] = 1.0
                data.ground_distance_matrix[other, customer] = 200.0
                data.ground_distance_matrix[customer, other] = 200.0
    if high_floor:
        high_customer = data.container_assignment[0]["customers"][0]
        data.is_high_floor[high_customer] = True
    state = initial_solution(data, config)
    return config, data, state


def _container_by_destination(state, warehouse: int) -> int:
    return next(
        int(container_id)
        for container_id, route in state.container_routes.items()
        if int(route["destination_warehouse"]) == int(warehouse)
    )


def _van_for_home(state, warehouse: int, index: int = 0) -> str:
    vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(warehouse)
    ]
    return vans[index]


def _drone_for_van(state, van_id: str) -> str:
    return next(
        drone_id
        for drone_id, carrier in sorted(state.drone_initial_carrier.items())
        if carrier == van_id
    )


def _service_source_base_state():
    config, data, state = _two_container_state(different_destinations=True)
    warehouse_1, warehouse_2 = [int(node) for node in data.transshipment_nodes[:2]]
    container_1 = _container_by_destination(state, warehouse_1)
    container_2 = _container_by_destination(state, warehouse_2)
    warehouse_1_customers = [int(customer) for customer in state.container_routes[container_1]["customers"]]
    warehouse_2_customers = [int(customer) for customer in state.container_routes[container_2]["customers"]]
    van_a = _van_for_home(state, warehouse_1)
    van_b = _van_for_home(state, warehouse_2)
    drone_from_w2 = _drone_for_van(state, van_b)
    extra_w1_drone = _drone_for_van(state, van_a)
    state.drone_initial_carrier.pop(extra_w1_drone)
    state.drone_home_warehouse.pop(extra_w1_drone, None)
    return (
        config,
        data,
        state,
        warehouse_1,
        warehouse_2,
        van_a,
        van_b,
        drone_from_w2,
        warehouse_1_customers,
        warehouse_2_customers,
    )


def test_feasible_drone_reposition_then_service_from_correct_container_van() -> None:
    (
        config,
        data,
        state,
        warehouse_1,
        warehouse_2,
        van_a,
        van_b,
        drone_id,
        w1_customers,
        w2_customers,
    ) = _service_source_base_state()
    reposition_customer = w2_customers[0]
    dock_node = w1_customers[0]
    service_customer = w1_customers[1]
    remaining_w1 = [
        customer
        for customer in w1_customers
        if customer not in {dock_node, service_customer}
    ]
    remaining_w2 = [
        customer
        for customer in w2_customers
        if customer != reposition_customer
    ]
    state.van_routes = {
        van_a: [warehouse_1, dock_node, *remaining_w1, warehouse_1],
        van_b: [warehouse_2, *remaining_w2, warehouse_2],
    }
    state.drone_sorties = [
        {
            "launch": warehouse_2,
            "customers": [reposition_customer],
            "recovery": dock_node,
            "launch_van_id": van_b,
            "recovery_van_id": van_a,
            "launch_position": 0,
            "recovery_position": 1,
            "drone_id": drone_id,
        },
        {
            "launch": dock_node,
            "customers": [service_customer],
            "recovery": dock_node,
            "launch_van_id": van_a,
            "recovery_van_id": van_a,
            "launch_position": 1,
            "recovery_position": 1,
            "drone_id": drone_id,
        },
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[reposition_customer] = "drone"
    state.service_mode[service_customer] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()

    _check_case(state, data, config, True)
    assert int(state.van_home[state.drone_initial_carrier[drone_id]]) == warehouse_2
    assert int(state.van_home[van_a]) == warehouse_1


def test_infeasible_drone_service_from_wrong_container_van() -> None:
    (
        config,
        data,
        state,
        warehouse_1,
        warehouse_2,
        van_a,
        van_b,
        drone_id,
        w1_customers,
        w2_customers,
    ) = _service_source_base_state()
    wrong_customer = w1_customers[0]
    remaining_w1 = [customer for customer in w1_customers if customer != wrong_customer]
    state.van_routes = {
        van_a: [warehouse_1, *remaining_w1, warehouse_1],
        van_b: [warehouse_2, *w2_customers, warehouse_2],
    }
    state.drone_sorties = [
        {
            "launch": warehouse_2,
            "customers": [wrong_customer],
            "recovery": warehouse_2,
            "launch_van_id": van_b,
            "recovery_van_id": van_b,
            "launch_position": 0,
            "recovery_position": len(state.van_routes[van_b]) - 1,
            "drone_id": drone_id,
        }
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[wrong_customer] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("is launched by" in item for item in violations)


def test_feasible_service_from_correct_van_recover_to_different_warehouse_van() -> None:
    (
        config,
        data,
        state,
        warehouse_1,
        warehouse_2,
        van_a,
        van_b,
        _,
        w1_customers,
        w2_customers,
    ) = _service_source_base_state()
    service_customer = w1_customers[0]
    recovery_node = w2_customers[0]
    drone_id = _drone_for_van(state, van_a)
    extra_w2_drone = _drone_for_van(state, van_b)
    state.drone_initial_carrier.pop(extra_w2_drone)
    state.drone_home_warehouse.pop(extra_w2_drone, None)
    remaining_w1 = [customer for customer in w1_customers if customer != service_customer]
    state.van_routes = {
        van_a: [warehouse_1, *remaining_w1, warehouse_1],
        van_b: [warehouse_2, recovery_node, *w2_customers[1:], warehouse_2],
    }
    state.drone_sorties = [
        {
            "launch": warehouse_1,
            "customers": [service_customer],
            "recovery": recovery_node,
            "launch_van_id": van_a,
            "recovery_van_id": van_b,
            "launch_position": 0,
            "recovery_position": 1,
            "drone_id": drone_id,
        }
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[service_customer] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()

    _check_case(state, data, config, True)
    assert int(state.van_home[van_b]) == warehouse_2


def test_infeasible_relaunch_from_old_wrong_carrier_after_recovery() -> None:
    (
        config,
        data,
        state,
        warehouse_1,
        warehouse_2,
        van_a,
        van_b,
        _,
        w1_customers,
        w2_customers,
    ) = _service_source_base_state()
    first_customer = w1_customers[0]
    second_customer = w1_customers[1]
    recovery_node = w2_customers[0]
    drone_id = _drone_for_van(state, van_a)
    remaining_w1 = [
        customer
        for customer in w1_customers
        if customer not in {first_customer, second_customer}
    ]
    state.van_routes = {
        van_a: [warehouse_1, *remaining_w1, warehouse_1],
        van_b: [warehouse_2, recovery_node, *w2_customers[1:], warehouse_2],
    }
    state.drone_sorties = [
        {
            "launch": warehouse_1,
            "customers": [first_customer],
            "recovery": recovery_node,
            "launch_van_id": van_a,
            "recovery_van_id": van_b,
            "launch_position": 0,
            "recovery_position": 1,
            "drone_id": drone_id,
        },
        {
            "launch": warehouse_1,
            "customers": [second_customer],
            "recovery": warehouse_1,
            "launch_van_id": van_a,
            "recovery_van_id": van_a,
            "launch_position": 0,
            "recovery_position": len(state.van_routes[van_a]) - 1,
            "drone_id": drone_id,
        },
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[first_customer] = "drone"
    state.service_mode[second_customer] = "drone"
    state.unassigned = []
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("before sortie but launches from" in item for item in violations)


def test_feasible_two_containers_same_transshipment() -> None:
    config, data, state = _two_container_state()

    _check_case(state, data, config, True)
    assert set(state.container_routes) == {0, 1}
    assert len({route["destination_warehouse"] for route in state.container_routes.values()}) == 1


def test_feasible_two_containers_different_transshipments() -> None:
    config, data, state = _two_container_state(different_destinations=True)

    _check_case(state, data, config, True)
    assert {route["destination_warehouse"] for route in state.container_routes.values()} == set(data.transshipment_nodes)


def test_infeasible_customer_served_from_wrong_container_warehouse() -> None:
    config, data, state = _two_container_state(different_destinations=True)
    by_destination = {
        int(route["destination_warehouse"]): int(container_id)
        for container_id, route in state.container_routes.items()
    }
    first, second = data.transshipment_nodes[:2]
    source_container = by_destination[first]
    wrong_customer = state.container_routes[source_container]["customers"][0]
    wrong_van = next(van_id for van_id, home in state.van_home.items() if int(home) == int(second))
    state.van_routes = {
        van_id: [node for node in route if node != wrong_customer]
        for van_id, route in state.van_routes.items()
    }
    state.van_routes.setdefault(wrong_van, [second, second]).insert(1, wrong_customer)
    state.service_mode[wrong_customer] = "van"
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("from container warehouse" in item for item in violations)


def test_infeasible_missing_container_unload() -> None:
    config, data, state = _two_container_state()
    state.container_routes.pop(1)

    violations = _check_case(state, data, config, False)
    assert any("references missing container" in item for item in violations)


def test_van_departure_is_gated_by_container_ready_time() -> None:
    config, data, state = _two_container_state()
    container = state.container_routes[0]
    warehouse = int(container["destination_warehouse"])
    container["unload_complete"] = 999.0
    state.metadata["warehouse_ready_time"] = {warehouse: 999.0}

    _check_case(state, data, config, True)
    sequence = state.timing["van_arrival_sequence_by_van"]
    first_van = next(
        van_id
        for van_id, route in state.van_routes.items()
        if int(route[0]) == warehouse
    )
    first_departure = float(sequence[first_van][0]["departure_time"])
    assert first_departure >= 999.0


def test_infeasible_duplicate_customer_service_across_containers() -> None:
    config, data, state = _two_container_state(different_destinations=True)
    duplicate_customer = data.customers[0]
    other_van = next(
        van_id
        for van_id, route in state.van_routes.items()
        if duplicate_customer not in route
    )
    state.van_routes[other_van].insert(1, duplicate_customer)
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("served more than once" in item for item in violations)


def test_feasible_multi_container_with_high_floor_drone() -> None:
    config, data, state = _two_container_state(high_floor=True)
    high_customers = [customer for customer, high in data.is_high_floor.items() if high]

    _check_case(state, data, config, True)
    assert high_customers
    assert all(state.service_mode[customer] == "drone" for customer in high_customers)


def test_infeasible_high_floor_served_by_van_in_multi_container() -> None:
    config, data, state = _two_container_state(high_floor=True)
    high_customer = next(customer for customer, high in data.is_high_floor.items() if high)
    for sortie in list(state.drone_sorties):
        if high_customer in sortie.get("customers", []):
            state.drone_sorties.remove(sortie)
    warehouse = int(state.order_assignment[high_customer]["assigned_transshipment"])
    van_id = next(van_id for van_id, home in state.van_home.items() if int(home) == warehouse)
    state.van_routes.setdefault(van_id, [warehouse, warehouse]).insert(1, high_customer)
    state.service_mode[high_customer] = "van"
    state.sync_primary_van_route()

    violations = _check_case(state, data, config, False)
    assert any("high-floor customer" in item for item in violations)


def test_two_container_cache_on_integration_smoke() -> None:
    config = build_config(
        num_customers=10,
        num_orders=10,
        num_transshipments=2,
        num_containers=2,
        iterations=20,
        seed=42,
        warehouse_num_vans={3: 3, 4: 3},
        drones_per_van=2,
        num_tractors=2,
        num_trailers=2,
        max_no_improve=None,
        early_stop_enabled=False,
        enable_local_feasibility_cache=True,
    )
    config.alns.collect_local_feasibility_cache_stats = True
    config.data.high_floor_ratio = 0.15
    data = generate_toy_data(config)
    result = run_c_alns(data, config)
    initial_feasible, initial_violations = check_solution_feasible(result.initial_state, data, config)
    best_feasible, best_violations = check_solution_feasible(result.best_state, data, config)
    best_cost, _ = objective(result.best_state, data, config)
    profile_cache = result.profile.get("local_feasibility_cache", {})
    served = result.best_state.get_van_customers() + result.best_state.get_drone_customers()

    assert initial_feasible is True, initial_violations
    assert best_feasible is True, best_violations
    assert best_cost > 0
    assert result.best_state.unassigned == []
    assert Counter(served) == Counter(data.customers)
    assert profile_cache.get("enabled") is True
