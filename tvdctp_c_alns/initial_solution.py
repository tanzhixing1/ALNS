from __future__ import annotations

from typing import List

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


def _make_drone_sortie(launch: int, customers, recovery: int) -> dict:
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
    }


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
    van_route = _nearest_neighbor_route(data, selected_transshipment)
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
        order_assignment=order_assignment,
        container_assignment=container_assignment,
        service_mode=service_mode,
        metadata={"route_endpoints": [van_route[0], van_route[-1]]},
    )

    candidates = sorted(
        data.customers,
        key=lambda customer: (not data.is_high_floor[customer], customer),
    )
    drone_candidates = []

    for customer in candidates:
        if customer not in state.van_route:
            continue
        if not _can_make_transshipment_sortie(
            customer, selected_transshipment, data, config
        ):
            continue

        pos = state.van_route.index(customer)
        pred = state.van_route[pos - 1]
        succ = state.van_route[pos + 1]
        van_saving = (
            data.ground_distance_matrix[pred, customer]
            + data.ground_distance_matrix[customer, succ]
            - data.ground_distance_matrix[pred, succ]
        ) * config.cost.van_cost_per_km
        drone_extra = drone_sortie_distance(
            (selected_transshipment, customer, selected_transshipment), data
        ) * config.cost.drone_cost_per_km + config.cost.drone_fixed_cost

        if data.is_high_floor[customer] or van_saving > drone_extra:
            drone_candidates.append(customer)

    while drone_candidates:
        seed = drone_candidates.pop(0)
        if seed not in state.van_route:
            continue
        sortie_customers = [seed]

        changed = True
        while changed:
            changed = False
            best_candidate = None
            best_distance = None
            for candidate in drone_candidates:
                if candidate not in state.van_route:
                    continue
                trial_customers = sortie_customers + [candidate]
                if not _can_make_transshipment_sortie(
                    trial_customers, selected_transshipment, data, config
                ):
                    continue
                trial_sortie = _make_drone_sortie(
                    selected_transshipment,
                    trial_customers,
                    selected_transshipment,
                )
                distance = drone_sortie_distance(trial_sortie, data)
                if best_distance is None or distance < best_distance:
                    best_candidate = candidate
                    best_distance = distance

            if best_candidate is not None:
                sortie_customers.append(best_candidate)
                drone_candidates.remove(best_candidate)
                changed = True

        if _can_make_transshipment_sortie(
            sortie_customers, selected_transshipment, data, config
        ):
            for customer in sortie_customers:
                state.van_route.remove(customer)
                state.service_mode[customer] = "drone"
            sortie = _make_drone_sortie(
                selected_transshipment, sortie_customers, selected_transshipment
            )
            sortie["launch_position"] = 0
            sortie["recovery_position"] = 0
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
            van_route=_nearest_neighbor_route(data, selected_transshipment),
            drone_sorties=[],
            order_assignment=order_assignment,
            container_assignment=container_assignment,
            service_mode={customer: "van" for customer in data.customers},
            metadata={"route_endpoints": [selected_transshipment]},
        )

    objective(state, data, config)
    return state
