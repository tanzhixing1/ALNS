from __future__ import annotations

from typing import Dict, List

from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import (
    check_solution_feasible,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_peak_payload,
)
from objective import objective
from state import TVDState


def _nearest_neighbor_route(data: InstanceData, selected_transshipment: int) -> List[int]:
    route = [selected_transshipment]
    unvisited = set(data.customers)
    current = selected_transshipment

    while unvisited:
        next_customer = min(
            unvisited, key=lambda customer: data.ground_distance_matrix[current, customer]
        )
        route.append(next_customer)
        unvisited.remove(next_customer)
        current = next_customer

    end_transshipment = min(
        data.transshipment_nodes,
        key=lambda node: data.ground_distance_matrix[current, node],
    )
    route.append(int(end_transshipment))
    return route


def _route_insert_cost(route: List[int], customer: int, data: InstanceData) -> tuple[float, int]:
    best_cost = None
    best_idx = 1
    for idx in range(1, len(route)):
        pred = route[idx - 1]
        succ = route[idx]
        cost = float(
            data.ground_distance_matrix[pred, customer]
            + data.ground_distance_matrix[customer, succ]
            - data.ground_distance_matrix[pred, succ]
        )
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_idx = idx
    return float(best_cost or 0.0), best_idx


def _route_payload(route: List[int], data: InstanceData) -> float:
    customers = [node for node in route if node in data.customers]
    return float(
        sum(data.demands[customer] for customer in customers)
        + sum(getattr(data, "pickup_demands", {}).get(customer, 0.0) for customer in customers)
    )


def _can_insert_customer(
    route: List[int],
    customer: int,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    demand = float(data.demands[customer]) + float(
        getattr(data, "pickup_demands", {}).get(customer, 0.0)
    )
    return _route_payload(route, data) + demand <= config.fleet.van_capacity_kg + 1e-9


def _build_initial_van_routes(
    data: InstanceData,
    config: TVDConfig,
    selected_transshipment: int,
    van_home: Dict[str, int],
) -> Dict[str, List[int]]:
    selected_vans = [
        van_id
        for van_id, home in sorted(van_home.items(), key=lambda item: int(item[0].split("_")[1]))
        if int(home) == int(selected_transshipment)
    ]
    if not selected_vans:
        selected_vans = [sorted(van_home, key=lambda item: int(item.split("_")[1]))[0]]

    active_vans = [selected_vans[0]]
    van_routes = {active_vans[0]: [selected_transshipment, selected_transshipment]}

    for customer in data.customers:
        best_van = None
        best_cost = None
        best_idx = 1
        for van_id in active_vans:
            if not _can_insert_customer(van_routes[van_id], customer, data, config):
                continue
            cost, idx = _route_insert_cost(van_routes[van_id], customer, data)
            if best_cost is None or cost < best_cost:
                best_van = van_id
                best_cost = cost
                best_idx = idx
        if best_van is None and len(active_vans) < len(selected_vans):
            best_van = selected_vans[len(active_vans)]
            active_vans.append(best_van)
            van_routes[best_van] = [selected_transshipment, selected_transshipment]
            best_idx = 1
        if best_van is None:
            for van_id in active_vans:
                cost, idx = _route_insert_cost(van_routes[van_id], customer, data)
                if best_cost is None or cost < best_cost:
                    best_van = van_id
                    best_cost = cost
                    best_idx = idx
        assert best_van is not None
        van_routes[best_van].insert(best_idx, int(customer))

    for van_id, route in van_routes.items():
        if len(route) > 1:
            last_customer = next((node for node in reversed(route) if node in data.customers), selected_transshipment)
            route[-1] = int(
                min(
                    data.transshipment_nodes,
                    key=lambda node: data.ground_distance_matrix[last_customer, node],
                )
            )
    return van_routes


def _truck_route(data: InstanceData, selected_transshipment: int) -> List[int]:
    if data.container_origin == selected_transshipment:
        return [data.truck_depot_node, selected_transshipment]
    return [data.truck_depot_node, data.container_origin, selected_transshipment]


def _select_transshipment(data: InstanceData, config: TVDConfig) -> int:
    best_node = data.transshipment_nodes[0]
    best_cost = None

    for candidate in data.transshipment_nodes:
        truck_distance = 0.0
        route = _truck_route(data, candidate)
        for idx in range(len(route) - 1):
            truck_distance += data.ground_distance_matrix[route[idx], route[idx + 1]]

        customer_distance = sum(
            data.ground_distance_matrix[candidate, customer]
            for customer in data.customers
        )
        estimated_cost = (
            truck_distance * config.cost.tractor_cost_per_km
            + customer_distance * config.cost.van_cost_per_km
        )
        if best_cost is None or estimated_cost < best_cost:
            best_cost = estimated_cost
            best_node = candidate

    return best_node


def _can_make_transshipment_sortie(
    customers,
    selected_transshipment: int,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    if isinstance(customers, int):
        customers = [customers]
    sortie = _make_drone_sortie(selected_transshipment, customers, selected_transshipment)
    return (
        config.fleet.drone_enabled
        and customers
        and all(data.drone_eligible[customer] for customer in customers)
        and drone_sortie_peak_payload(sortie, data, config) <= config.fleet.drone_capacity_kg
        and drone_sortie_distance(sortie, data) <= config.fleet.drone_endurance_km
        and drone_sortie_energy(sortie, data, config) <= config.fleet.drone_battery_capacity_kwh
    )


def _make_drone_sortie(
    launch: int,
    customers,
    recovery: int,
    drone_id: str = "",
    launch_van_id: str = "",
    recovery_van_id: str = "",
) -> dict:
    if isinstance(customers, int):
        customers = [customers]
    return {
        "launch": int(launch),
        "customers": [int(customer) for customer in customers],
        "recovery": int(recovery),
        "launch_time": 0.0,
        "recovery_time": 0.0,
        "van_waiting_time": 0.0,
        "drone_waiting_time": 0.0,
        "same_node": bool(launch == recovery),
        "drone_id": drone_id,
        "launch_van_id": launch_van_id,
        "recovery_van_id": recovery_van_id,
    }


def _first_drone_for_van(state: TVDState, van_id: str) -> str:
    return next(
        (
            drone_id
            for drone_id, carrier in state.drone_initial_carrier.items()
            if carrier == van_id
        ),
        "",
    )


def _remove_customers_from_van_routes(
    routes: Dict[str, List[int]], customers: List[int]
) -> Dict[str, List[int]]:
    remove_set = {int(customer) for customer in customers}
    return {
        van_id: [node for node in route if int(node) not in remove_set]
        for van_id, route in routes.items()
    }


def _candidate_sortie_is_feasible(
    state: TVDState,
    sortie: dict,
    sortie_customers: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    trial = state.copy()
    trial.van_routes = _remove_customers_from_van_routes(
        trial.van_routes, sortie_customers
    )
    trial.sync_primary_van_route()
    trial.drone_sorties.append(sortie)
    for customer in sortie_customers:
        trial.service_mode[int(customer)] = "drone"
    feasible, violations = check_solution_feasible(trial, data, config)
    if feasible:
        return True
    ignored = {
        f"high-floor customer {customer} must be served by drone."
        for customer, high_floor in data.is_high_floor.items()
        if high_floor and customer not in sortie_customers
    }
    return all(violation in ignored for violation in violations)


def _best_drone_sortie_for_customers(
    state: TVDState,
    sortie_customers: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> dict | None:
    if not config.fleet.drone_enabled:
        return None
    if not sortie_customers or any(
        not data.drone_eligible.get(int(customer), False)
        for customer in sortie_customers
    ):
        return None

    best_sortie = None
    best_cost = None
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for launch_van_id, launch_route in routes.items():
        drone_id = _first_drone_for_van(state, launch_van_id)
        if not drone_id:
            continue
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            if int(launch) in sortie_customers:
                continue
            for recovery_van_id, recovery_route in routes.items():
                for recovery_pos, recovery in enumerate(recovery_route):
                    if int(recovery) in sortie_customers:
                        continue
                    if launch_van_id == recovery_van_id and recovery_pos < launch_pos:
                        continue
                    sortie = _make_drone_sortie(
                        launch,
                        sortie_customers,
                        recovery,
                        drone_id=drone_id,
                        launch_van_id=launch_van_id,
                        recovery_van_id=recovery_van_id,
                    )
                    sortie["launch_position"] = int(launch_pos)
                    sortie["recovery_position"] = int(recovery_pos)
                    if (
                        drone_sortie_peak_payload(sortie, data, config)
                        > config.fleet.drone_capacity_kg
                        or drone_sortie_distance(sortie, data)
                        > config.fleet.drone_endurance_km
                        or drone_sortie_energy(sortie, data, config)
                        > config.fleet.drone_battery_capacity_kwh
                    ):
                        continue
                    if not _candidate_sortie_is_feasible(
                        state, sortie, sortie_customers, data, config
                    ):
                        continue
                    cost = (
                        drone_sortie_distance(sortie, data)
                        * config.cost.drone_cost_per_km
                        + config.cost.drone_fixed_cost
                    )
                    if best_cost is None or cost < best_cost:
                        best_cost = cost
                        best_sortie = sortie
    return best_sortie


def _van_saving_for_customers(
    state: TVDState,
    customers: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> float:
    saving = 0.0
    for customer in customers:
        for route in state.van_routes.values():
            if customer not in route:
                continue
            pos = route.index(customer)
            pred = route[pos - 1]
            succ = route[pos + 1]
            saving += (
                data.ground_distance_matrix[pred, customer]
                + data.ground_distance_matrix[customer, succ]
                - data.ground_distance_matrix[pred, succ]
            ) * config.cost.van_cost_per_km
            break
    return float(saving)


def _build_assignments(data: InstanceData, selected_transshipment: int):
    order_assignment = {}
    container_assignment = copy_container_assignment(data, selected_transshipment)

    for order in data.orders:
        customer = int(order["customer_id"])
        container = int(order["container_id"])
        order_assignment[customer] = {
            "order_id": int(order["order_id"]),
            "customer_id": customer,
            "container_id": container,
            "container_origin": int(order["container_origin"]),
            "assigned_transshipment": selected_transshipment,
            "demand": float(order["demand"]),
            "pickup_demand": float(order.get("pickup_demand", 0.0)),
            "service_required": bool(order["service_required"]),
        }

    return order_assignment, container_assignment


def copy_container_assignment(data: InstanceData, selected_transshipment: int):
    container_assignment = {}
    for container_id, assignment in data.container_assignment.items():
        container_assignment[int(container_id)] = {
            "container_id": int(assignment["container_id"]),
            "origin_node": int(assignment["origin_node"]),
            "origin_type": str(assignment["origin_type"]),
            "candidate_transshipments": list(assignment["candidate_transshipments"]),
            "selected_transshipment": selected_transshipment,
            "orders": list(assignment["orders"]),
            "customers": list(assignment["customers"]),
        }
    return container_assignment


def initial_solution(data: InstanceData, config: TVDConfig) -> TVDState:
    """
    论文第 5.1.1 节的三阶段构造 toy 版：
    1. 固定港口到中转仓；
    2. 最近邻构造 van 主路线；
    3. 将高楼/有收益的低楼客户转为 drone sortie。
    """

    selected_transshipment = _select_transshipment(data, config)
    truck_route = _truck_route(data, selected_transshipment)
    van_home = config.build_van_home(data.transshipment_nodes)
    drone_initial_carrier = config.build_drone_initial_carrier(data.transshipment_nodes)
    drone_home_warehouse = config.build_drone_home_warehouse(data.transshipment_nodes)
    van_routes = _build_initial_van_routes(data, config, selected_transshipment, van_home)
    primary_van = sorted(van_routes, key=lambda item: int(item.split("_")[1]))[0]
    van_route = van_routes[primary_van].copy()
    service_mode = {customer: "van" for customer in data.customers}
    order_assignment, container_assignment = _build_assignments(
        data, selected_transshipment
    )
    state = TVDState(
        port_node=data.port_node,
        truck_depot_node=data.truck_depot_node,
        transshipment_nodes=data.transshipment_nodes.copy(),
        selected_transshipment=selected_transshipment,
        container_origin=data.container_origin,
        truck_route=truck_route,
        van_route=van_route,
        van_routes=van_routes,
        van_home=van_home,
        drone_initial_carrier=drone_initial_carrier,
        drone_home_warehouse=drone_home_warehouse,
        order_assignment=order_assignment,
        container_assignment=container_assignment,
        service_mode=service_mode,
        metadata={
            "route_endpoints": sorted(set(data.transshipment_nodes)),
            "warehouse_num_vans": config.warehouse_num_vans(data.transshipment_nodes),
            "warehouse_num_drones": config.warehouse_num_drones(data.transshipment_nodes),
            "drones_per_van": config.fleet.drones_per_van,
        },
    )

    candidates = sorted(
        data.customers,
        key=lambda customer: (not data.is_high_floor[customer], customer),
    )
    drone_candidates = []

    for customer in candidates:
        if not config.fleet.drone_enabled or not data.drone_eligible.get(customer, False):
            continue
        if any(customer in route for route in state.van_routes.values()):
            drone_candidates.append(customer)

    while drone_candidates:
        seed = drone_candidates.pop(0)
        route_owner = next(
            (
                van_id
                for van_id, route in state.van_routes.items()
                if seed in route
            ),
            None,
        )
        if route_owner is None:
            continue
        sortie_customers = [seed]

        changed = True
        while changed:
            changed = False
            best_candidate = None
            best_distance = None
            for candidate in drone_candidates:
                trial_customers = sortie_customers + [candidate]
                trial_sortie = _best_drone_sortie_for_customers(
                    state, trial_customers, data, config
                )
                if trial_sortie is None:
                    continue
                distance = drone_sortie_distance(trial_sortie, data)
                if best_distance is None or distance < best_distance:
                    best_candidate = candidate
                    best_distance = distance

            if best_candidate is not None:
                sortie_customers.append(best_candidate)
                drone_candidates.remove(best_candidate)
                changed = True

        sortie = _best_drone_sortie_for_customers(
            state, sortie_customers, data, config
        )
        if sortie is not None:
            drone_cost = (
                drone_sortie_distance(sortie, data) * config.cost.drone_cost_per_km
                + config.cost.drone_fixed_cost
            )
            van_saving = _van_saving_for_customers(
                state, sortie_customers, data, config
            )
            if (
                not any(data.is_high_floor[customer] for customer in sortie_customers)
                and van_saving <= drone_cost
            ):
                continue
            for customer in sortie_customers:
                state.service_mode[customer] = "drone"
            state.van_routes = _remove_customers_from_van_routes(
                state.van_routes, sortie_customers
            )
            state.sync_primary_van_route()
            state.drone_sorties.append(sortie)

    feasible, _ = check_solution_feasible(state, data, config)
    if not feasible:
        # 如果 toy 随机点导致无人机不可行，至少返回纯地面可运行解，并让 objective 给出惩罚。
        state = TVDState(
            port_node=data.port_node,
            truck_depot_node=data.truck_depot_node,
            transshipment_nodes=data.transshipment_nodes.copy(),
            selected_transshipment=selected_transshipment,
            container_origin=data.container_origin,
            truck_route=truck_route,
            van_route=van_route,
            van_routes=van_routes,
            van_home=van_home,
            drone_initial_carrier=drone_initial_carrier,
            drone_home_warehouse=drone_home_warehouse,
            drone_sorties=[],
            order_assignment=order_assignment,
            container_assignment=container_assignment,
            service_mode={customer: "van" for customer in data.customers},
            metadata={
                "route_endpoints": sorted(set(data.transshipment_nodes)),
                "warehouse_num_vans": config.warehouse_num_vans(data.transshipment_nodes),
                "warehouse_num_drones": config.warehouse_num_drones(data.transshipment_nodes),
                "drones_per_van": config.fleet.drones_per_van,
            },
        )

    objective(state, data, config)
    return state
