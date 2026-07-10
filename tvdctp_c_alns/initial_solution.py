from __future__ import annotations

import time
import warnings
from typing import Dict, List, Tuple

from alns_profile import snapshot_profile
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


def _travel_minutes(distance: float, speed_kmph: float) -> float:
    return float(distance) / speed_kmph * 60.0


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


def _route_insert_delta(route: List[int], customer: int, idx: int, data: InstanceData) -> float:
    pred = route[idx - 1]
    succ = route[idx]
    return float(
        data.ground_distance_matrix[pred, customer]
        + data.ground_distance_matrix[customer, succ]
        - data.ground_distance_matrix[pred, succ]
    )


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


def _route_time_window_feasible(
    route: List[int],
    start_time: float,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    current_time = float(start_time)
    previous_node = int(route[0]) if route else 0
    for idx, node in enumerate(route):
        node = int(node)
        if idx > 0:
            current_time += _travel_minutes(
                data.ground_distance_matrix[previous_node, node],
                config.fleet.van_speed_kmph,
            )
        if node in data.customers:
            earliest, latest = data.time_windows.get(node, (0.0, float("inf")))
            service_start = max(current_time, float(earliest))
            if service_start > float(latest) + 1e-9:
                return False
            current_time = service_start + float(data.service_times.get(node, 0.0))
        previous_node = node
    return True


def _route_insert_feasible(
    route: List[int],
    customer: int,
    idx: int,
    start_time: float,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    candidate_route = route[:idx] + [int(customer)] + route[idx:]
    return (
        _route_payload(candidate_route, data) <= config.fleet.van_capacity_kg + 1e-9
        and _route_time_window_feasible(candidate_route, start_time, data, config)
    )


def _build_initial_van_routes(
    data: InstanceData,
    config: TVDConfig,
    selected_transshipment: int,
    van_home: Dict[str, int],
    customers: List[int] | None = None,
    start_time: float = 0.0,
) -> Tuple[Dict[str, List[int]], List[int], Dict[int, str]]:
    route_customers = sorted(
        [int(customer) for customer in (customers if customers is not None else data.customers)],
        key=lambda customer: (
            float(data.time_windows.get(customer, (0.0, float("inf")))[1]) - float(start_time),
            float(data.time_windows.get(customer, (0.0, float("inf")))[1]),
            float(data.time_windows.get(customer, (0.0, float("inf")))[0]),
            int(customer),
        ),
    )
    selected_vans = [
        van_id
        for van_id, home in sorted(van_home.items(), key=lambda item: int(item[0].split("_")[1]))
        if int(home) == int(selected_transshipment)
    ]
    if not selected_vans:
        selected_vans = [sorted(van_home, key=lambda item: int(item.split("_")[1]))[0]]

    active_vans = [selected_vans[0]]
    van_routes = {active_vans[0]: [selected_transshipment, selected_transshipment]}
    target_customers_per_van = max(
        6,
        (len(route_customers) + max(len(selected_vans), 1) - 1) // max(len(selected_vans), 1),
    )
    deferred_customers: List[int] = []
    failure_reasons: Dict[int, str] = {}

    for customer in route_customers:
        best_van = None
        best_cost = None
        best_idx = 1
        for van_id in active_vans:
            assigned_count = sum(1 for node in van_routes[van_id] if node in data.customers)
            if (
                assigned_count >= target_customers_per_van
                and len(active_vans) < len(selected_vans)
            ):
                continue
            for idx in range(1, len(van_routes[van_id])):
                if not _route_insert_feasible(
                    van_routes[van_id],
                    customer,
                    idx,
                    start_time,
                    data,
                    config,
                ):
                    continue
                cost = _route_insert_delta(van_routes[van_id], customer, idx, data)
                if best_cost is None or cost < best_cost:
                    best_van = van_id
                    best_cost = cost
                    best_idx = idx
        if best_van is None and len(active_vans) < len(selected_vans):
            candidate_van = selected_vans[len(active_vans)]
            candidate_route = [selected_transshipment, selected_transshipment]
            if _route_insert_feasible(
                candidate_route,
                customer,
                1,
                start_time,
                data,
                config,
            ):
                best_van = candidate_van
                active_vans.append(best_van)
                van_routes[best_van] = candidate_route
                best_idx = 1
        if best_van is None:
            deferred_customers.append(int(customer))
            unused_vans = selected_vans[len(active_vans) :]
            failure_reasons[int(customer)] = (
                f"customer {int(customer)} cannot be inserted without violating "
                f"van capacity/time window; tried active vans {list(active_vans)}; "
                f"tried unused vans {list(unused_vans)}."
            )
            continue
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
    return van_routes, deferred_customers, failure_reasons


def _container_unload_duration(config: TVDConfig) -> float:
    return float(config.fleet.container_unload_time or config.data.service_time_min)


def _container_customer_ids(data: InstanceData, container_id: int) -> List[int]:
    assignment = data.container_assignment[int(container_id)]
    return [int(customer) for customer in assignment.get("customers", [])]


def _choose_container_destination(
    data: InstanceData,
    config: TVDConfig,
    container_id: int,
    selected_counts: Dict[int, int] | None = None,
) -> int:
    assignment = data.container_assignment[int(container_id)]
    origin = int(assignment["origin_node"])
    customers = _container_customer_ids(data, int(container_id))
    warehouse_vans = config.warehouse_num_vans(data.transshipment_nodes)
    selected_counts = selected_counts or {}
    scored_candidates: List[Tuple[float, Tuple[int, int], int]] = []
    for warehouse in data.transshipment_nodes:
        average_customer_distance = (
            sum(float(data.ground_distance_matrix[int(warehouse), customer]) for customer in customers)
            / max(len(customers), 1)
        )
        drone_penalty = 0.0
        if any(data.is_high_floor.get(customer, False) and not data.drone_eligible.get(customer, False) for customer in customers):
            drone_penalty += 1_000_000.0
        if warehouse_vans.get(int(warehouse), 0) <= 0:
            drone_penalty += 1_000_000.0
        base_score = (
            float(data.ground_distance_matrix[origin, int(warehouse)])
            + average_customer_distance
            + drone_penalty
        )
        tie_breaker = (
            int(selected_counts.get(int(warehouse), 0)),
            int(warehouse),
        )
        scored_candidates.append((float(base_score), tie_breaker, int(warehouse)))

    best_base_score = min(score for score, _, _ in scored_candidates)
    near_tie_epsilon = max(1e-6, 0.01 * max(abs(best_base_score), 1.0))
    near_tie_candidates = [
        item
        for item in scored_candidates
        if item[0] <= best_base_score + near_tie_epsilon
    ]
    _, _, best_warehouse = min(
        near_tie_candidates,
        key=lambda item: (item[1], item[0], item[2]),
    )
    return int(best_warehouse)


def _decide_container_destinations(
    data: InstanceData,
    config: TVDConfig,
) -> Dict[int, int]:
    destinations: Dict[int, int] = {}
    selected_counts: Dict[int, int] = {}

    def assignment_priority(container_id: int) -> Tuple[float, float, int]:
        customers = _container_customer_ids(data, int(container_id))
        earliest_due = min(
            (
                float(data.time_windows.get(customer, (0.0, float("inf")))[1])
                for customer in customers
            ),
            default=float("inf"),
        )
        raw_scores: List[float] = []
        assignment = data.container_assignment[int(container_id)]
        origin = int(assignment["origin_node"])
        for warehouse in data.transshipment_nodes:
            average_customer_distance = (
                sum(float(data.ground_distance_matrix[int(warehouse), customer]) for customer in customers)
                / max(len(customers), 1)
            )
            raw_scores.append(
                float(data.ground_distance_matrix[origin, int(warehouse)])
                + average_customer_distance
            )
        best_raw_score = min(raw_scores) if raw_scores else 0.0
        return (earliest_due, -best_raw_score, int(container_id))

    for container_id in sorted(data.container_assignment, key=assignment_priority):
        destination = _choose_container_destination(
            data,
            config,
            int(container_id),
            selected_counts=selected_counts,
        )
        destinations[int(container_id)] = int(destination)
        selected_counts[int(destination)] = selected_counts.get(int(destination), 0) + 1
    return destinations


def _container_service_priority(
    data: InstanceData,
    container_id: int,
    destination: int,
) -> Tuple[float, float, int]:
    assignment = data.container_assignment[int(container_id)]
    origin = int(assignment["origin_node"])
    customers = _container_customer_ids(data, int(container_id))
    earliest_due = min(
        (float(data.time_windows.get(customer, (0.0, float("inf")))[1]) for customer in customers),
        default=float("inf"),
    )
    distance = float(data.ground_distance_matrix[origin, int(destination)])
    return (earliest_due, distance, int(container_id))


def _event(
    node: int,
    event: str,
    arrival_time: float,
    departure_time: float,
    haul_status: str,
    trailer_id: str = "",
    container_id: int | None = None,
) -> Dict[str, object]:
    row: Dict[str, object] = {
        "node": int(node),
        "event": event,
        "trailer_id": trailer_id,
        "arrival_time": float(arrival_time),
        "departure_time": float(departure_time),
        "haul_status": haul_status,
    }
    if container_id is not None:
        row["container_id"] = int(container_id)
    return row


def _build_stage1_drayage(
    data: InstanceData,
    config: TVDConfig,
    destinations: Dict[int, int],
) -> Tuple[
    Dict[str, List[Dict[str, object]]],
    Dict[int, Dict[str, object]],
    Dict[str, int],
    Dict[str, int],
    List[int],
    Dict[int, float],
]:
    tractor_home = config.build_tractor_home()
    trailer_home = config.build_trailer_home(data.trailer_depot_node)
    if not tractor_home:
        tractor_home = {"tractor_0": int(data.tractor_depot_node)}
    if not trailer_home:
        trailer_home = {"trailer_0": int(data.trailer_depot_node)}

    tractor_state = {
        tractor_id: {
            "time": 0.0,
            "node": int(home),
            "attached_trailer": "",
        }
        for tractor_id, home in tractor_home.items()
    }
    trailer_state = {
        trailer_id: {
            "time": 0.0,
            "node": int(home),
            "attached_to": "",
        }
        for trailer_id, home in trailer_home.items()
    }
    tractor_routes: Dict[str, List[Dict[str, object]]] = {
        tractor_id: [] for tractor_id in tractor_home
    }
    container_routes: Dict[int, Dict[str, object]] = {}

    service_order = sorted(
        destinations,
        key=lambda container_id: _container_service_priority(
            data, int(container_id), int(destinations[int(container_id)])
        ),
    )

    for sequence_idx, container_id in enumerate(service_order):
        origin = int(data.container_assignment[int(container_id)]["origin_node"])
        destination = int(destinations[int(container_id)])
        best_choice = None
        best_score = None
        for tractor_id, tractor in tractor_state.items():
            for trailer_id, trailer in trailer_state.items():
                attached = str(tractor["attached_trailer"])
                trailer_attached_to = str(trailer["attached_to"])
                if attached and attached != trailer_id:
                    continue
                if trailer_attached_to and trailer_attached_to != tractor_id:
                    continue
                start_time = max(float(tractor["time"]), float(trailer["time"]))
                current_node = int(tractor["node"])
                if attached == trailer_id:
                    pre_origin_distance = float(data.ground_distance_matrix[current_node, origin])
                else:
                    trailer_node = int(trailer["node"])
                    pre_origin_distance = float(
                        data.ground_distance_matrix[current_node, trailer_node]
                        + data.ground_distance_matrix[trailer_node, origin]
                    )
                loaded_distance = float(data.ground_distance_matrix[origin, destination])
                score = start_time + pre_origin_distance + loaded_distance
                if best_score is None or score < best_score:
                    best_score = score
                    best_choice = (tractor_id, trailer_id)
        if best_choice is None:
            raise ValueError("No tractor/trailer pair can serve container.")

        tractor_id, trailer_id = best_choice
        tractor = tractor_state[tractor_id]
        trailer = trailer_state[trailer_id]
        route = tractor_routes.setdefault(tractor_id, [])
        if not route:
            home = int(tractor_home[tractor_id])
            route.append(
                _event(
                    home,
                    "depart_tractor_depot",
                    0.0,
                    0.0,
                    "tractor_only",
                )
            )

        current_time = max(float(tractor["time"]), float(trailer["time"]))
        current_node = int(tractor["node"])
        if str(tractor["attached_trailer"]) != trailer_id:
            trailer_node = int(trailer["node"])
            current_time += _travel_minutes(
                data.ground_distance_matrix[current_node, trailer_node],
                config.fleet.tractor_speed_kmph,
            )
            attach_arrival = current_time
            current_time += float(config.fleet.trailer_attach_time)
            route.append(
                _event(
                    trailer_node,
                    "attach_trailer",
                    attach_arrival,
                    current_time,
                    "empty_trailer",
                    trailer_id=trailer_id,
                )
            )
            tractor["attached_trailer"] = trailer_id
            trailer["attached_to"] = tractor_id
            current_node = trailer_node

        current_time += _travel_minutes(
            data.ground_distance_matrix[current_node, origin],
            config.fleet.tractor_speed_kmph,
        )
        load_start = current_time
        load_complete = load_start + float(config.fleet.container_load_time)
        route.append(
            _event(
                origin,
                "load_container",
                load_start,
                load_complete,
                "loaded_trailer",
                trailer_id=trailer_id,
                container_id=int(container_id),
            )
        )

        current_time = load_complete + _travel_minutes(
            data.ground_distance_matrix[origin, destination],
            config.fleet.tractor_speed_kmph,
        )
        unload_start = current_time
        unload_complete = unload_start + _container_unload_duration(config)
        route.append(
            _event(
                destination,
                "unload_container",
                unload_start,
                unload_complete,
                "empty_trailer",
                trailer_id=trailer_id,
                container_id=int(container_id),
            )
        )

        tractor["time"] = unload_complete
        tractor["node"] = destination
        trailer["time"] = unload_complete
        trailer["node"] = destination
        assigned_orders = list(data.container_assignment[int(container_id)].get("assigned_orders", []))
        container_routes[int(container_id)] = {
            "origin": origin,
            "destination_warehouse": destination,
            "assigned_orders": assigned_orders,
            "customers": _container_customer_ids(data, int(container_id)),
            "tractor_id": tractor_id,
            "trailer_id": trailer_id,
            "service_sequence_index": int(sequence_idx),
            "load_start": float(load_start),
            "load_complete": float(load_complete),
            "unload_start": float(unload_start),
            "unload_complete": float(unload_complete),
        }

    for tractor_id, tractor in tractor_state.items():
        trailer_id = str(tractor["attached_trailer"])
        if not trailer_id:
            continue
        route = tractor_routes[tractor_id]
        current_node = int(tractor["node"])
        current_time = float(tractor["time"])
        trailer_node = int(trailer_home[trailer_id])
        current_time += _travel_minutes(
            data.ground_distance_matrix[current_node, trailer_node],
            config.fleet.tractor_speed_kmph,
        )
        detach_arrival = current_time
        current_time += float(config.fleet.trailer_detach_time)
        route.append(
            _event(
                trailer_node,
                "detach_trailer",
                detach_arrival,
                current_time,
                "tractor_only",
                trailer_id=trailer_id,
            )
        )
        tractor_home_node = int(tractor_home[tractor_id])
        current_time += _travel_minutes(
            data.ground_distance_matrix[trailer_node, tractor_home_node],
            config.fleet.tractor_speed_kmph,
        )
        route.append(
            _event(
                tractor_home_node,
                "return_tractor_depot",
                current_time,
                current_time,
                "tractor_only",
            )
        )
        tractor["time"] = current_time
        tractor["node"] = tractor_home_node
        tractor["attached_trailer"] = ""

    warehouse_ready_time: Dict[int, float] = {}
    for item in container_routes.values():
        warehouse = int(item["destination_warehouse"])
        warehouse_ready_time[warehouse] = max(
            warehouse_ready_time.get(warehouse, 0.0),
            float(item["unload_complete"]),
        )
    first_route = next((route for route in tractor_routes.values() if route), [])
    legacy_truck_route = [int(item["node"]) for item in first_route] if first_route else []
    return (
        {tractor_id: route for tractor_id, route in tractor_routes.items() if route},
        container_routes,
        tractor_home,
        trailer_home,
        legacy_truck_route,
        warehouse_ready_time,
    )


def _build_initial_vans_for_container_routes(
    data: InstanceData,
    config: TVDConfig,
    container_routes: Dict[int, Dict[str, object]],
    warehouse_ready_time: Dict[int, float],
    van_home: Dict[str, int],
) -> Tuple[Dict[str, List[int]], List[int], Dict[int, str]]:
    customers_by_warehouse: Dict[int, List[int]] = {}
    for route in container_routes.values():
        warehouse = int(route["destination_warehouse"])
        for customer in route.get("customers", []):
            customers_by_warehouse.setdefault(warehouse, []).append(int(customer))

    van_routes: Dict[str, List[int]] = {}
    deferred_customers: List[int] = []
    failure_reasons: Dict[int, str] = {}
    for warehouse, customers in sorted(customers_by_warehouse.items()):
        warehouse_routes, deferred, reasons = _build_initial_van_routes(
            data,
            config,
            int(warehouse),
            van_home,
            customers=customers,
            start_time=float(warehouse_ready_time.get(int(warehouse), 0.0)),
        )
        van_routes.update(warehouse_routes)
        deferred_customers.extend(deferred)
        failure_reasons.update(reasons)
    return van_routes, deferred_customers, failure_reasons


def _container_for_customer(data: InstanceData, customer: int) -> int | None:
    customer = int(customer)
    for container_id, assignment in data.container_assignment.items():
        if customer in [int(item) for item in assignment.get("customers", [])]:
            return int(container_id)
    return None


def _retry_destinations_after_van_failure(
    data: InstanceData,
    config: TVDConfig,
    destinations: Dict[int, int],
    deferred_customers: List[int],
    van_home: Dict[str, int],
) -> Tuple[
    Dict[int, int],
    Dict[str, List[Dict[str, object]]],
    Dict[int, Dict[str, object]],
    Dict[str, int],
    Dict[str, int],
    List[int],
    Dict[int, float],
    Dict[str, List[int]],
    List[int],
    Dict[int, str],
] | None:
    if not deferred_customers or len(destinations) <= 1 or len(data.transshipment_nodes) <= 1:
        return None

    deferred_containers = {
        container_id
        for customer in deferred_customers
        for container_id in [_container_for_customer(data, int(customer))]
        if container_id is not None and container_id in destinations
    }
    problem_warehouses = {int(destinations[container_id]) for container_id in deferred_containers}
    candidate_containers = [
        int(container_id)
        for container_id, warehouse in sorted(destinations.items())
        if int(warehouse) in problem_warehouses
    ]

    best_result = None
    best_score = None
    for container_id in candidate_containers:
        current_warehouse = int(destinations[container_id])
        for warehouse in sorted(int(node) for node in data.transshipment_nodes):
            if warehouse == current_warehouse:
                continue
            candidate_destinations = dict(destinations)
            candidate_destinations[int(container_id)] = int(warehouse)
            try:
                (
                    tractor_routes,
                    container_routes,
                    tractor_home,
                    trailer_home,
                    truck_route,
                    warehouse_ready_time,
                ) = _build_stage1_drayage(data, config, candidate_destinations)
                van_routes, deferred, failure_reasons = _build_initial_vans_for_container_routes(
                    data,
                    config,
                    container_routes,
                    warehouse_ready_time,
                    van_home,
                )
            except ValueError:
                continue
            score = (
                len(deferred),
                max(warehouse_ready_time.values(), default=0.0),
                int(container_id),
                int(warehouse),
            )
            if best_score is None or score < best_score:
                best_score = score
                best_result = (
                    candidate_destinations,
                    tractor_routes,
                    container_routes,
                    tractor_home,
                    trailer_home,
                    truck_route,
                    warehouse_ready_time,
                    van_routes,
                    deferred,
                    failure_reasons,
                )
            if not deferred:
                return best_result

    if best_result is not None and best_score is not None and best_score[0] < len(deferred_customers):
        return best_result
    return None


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
    construction_unassigned: List[int] | None = None,
) -> bool:
    trial = state.copy()
    trial.van_routes = _remove_customers_from_van_routes(
        trial.van_routes, sortie_customers
    )
    trial.sync_primary_van_route()
    trial.drone_sorties.append(sortie)
    if construction_unassigned is not None:
        trial.unassigned = [
            int(customer)
            for customer in construction_unassigned
            if int(customer) not in {int(item) for item in sortie_customers}
        ]
        for customer in trial.unassigned:
            trial.service_mode[int(customer)] = "drone"
    for customer in sortie_customers:
        trial.service_mode[int(customer)] = "drone"
    feasible, violations = check_solution_feasible(trial, data, config)
    if feasible:
        return True
    if construction_unassigned is not None:
        return bool(violations) and all(
            str(violation).startswith("unassigned customers remain:")
            for violation in violations
        )
    return False


def _best_drone_sortie_for_customers(
    state: TVDState,
    sortie_customers: List[int],
    data: InstanceData,
    config: TVDConfig,
    construction_unassigned: List[int] | None = None,
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
                        state,
                        sortie,
                        sortie_customers,
                        data,
                        config,
                        construction_unassigned=construction_unassigned,
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


def _apply_drone_sortie_for_customers(
    state: TVDState,
    sortie_customers: List[int],
    data: InstanceData,
    config: TVDConfig,
    construction_unassigned: List[int] | None = None,
) -> bool:
    sortie = _best_drone_sortie_for_customers(
        state,
        sortie_customers,
        data,
        config,
        construction_unassigned=construction_unassigned,
    )
    if sortie is None:
        return False
    for customer in sortie_customers:
        state.service_mode[int(customer)] = "drone"
        if int(customer) in state.unassigned:
            state.unassigned.remove(int(customer))
    state.van_routes = _remove_customers_from_van_routes(
        state.van_routes, sortie_customers
    )
    state.sync_primary_van_route()
    state.drone_sorties.append(sortie)
    return True


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


def _build_assignments(data: InstanceData, container_routes: Dict[int, Dict[str, object]]):
    order_assignment = {}
    container_assignment = copy_container_assignment(data, container_routes)

    for order in data.orders:
        customer = int(order["customer_id"])
        container = int(order["container_id"])
        destination = int(container_routes[container]["destination_warehouse"])
        order_assignment[customer] = {
            "order_id": int(order["order_id"]),
            "customer_id": customer,
            "container_id": container,
            "container_origin": int(order["container_origin"]),
            "assigned_transshipment": destination,
            "demand": float(order["demand"]),
            "pickup_demand": float(order.get("pickup_demand", 0.0)),
            "service_required": bool(order["service_required"]),
        }

    return order_assignment, container_assignment


def copy_container_assignment(data: InstanceData, container_routes: Dict[int, Dict[str, object]]):
    container_assignment = {}
    for container_id, assignment in data.container_assignment.items():
        route = container_routes.get(int(container_id), {})
        destination = route.get("destination_warehouse")
        container_assignment[int(container_id)] = {
            "container_id": int(assignment["container_id"]),
            "origin_node": int(assignment["origin_node"]),
            "origin": int(assignment.get("origin", assignment["origin_node"])),
            "origin_type": str(assignment["origin_type"]),
            "candidate_transshipments": list(assignment["candidate_transshipments"]),
            "selected_transshipment": int(destination) if destination is not None else None,
            "destination_warehouse": int(destination) if destination is not None else None,
            "assigned_orders": list(assignment.get("assigned_orders", assignment["orders"])),
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

    initial_profile_start = snapshot_profile()
    initial_timing: Dict[str, float] = {}

    stage_start = time.perf_counter()
    destinations = _decide_container_destinations(data, config)
    initial_timing["t_decide_container_destinations"] = (
        time.perf_counter() - stage_start
    )
    van_home = config.build_van_home(data.transshipment_nodes)

    stage_start = time.perf_counter()
    (
        tractor_routes,
        container_routes,
        tractor_home,
        trailer_home,
        truck_route,
        warehouse_ready_time,
    ) = _build_stage1_drayage(data, config, destinations)
    initial_timing["t_build_stage1_drayage"] = time.perf_counter() - stage_start

    stage_start = time.perf_counter()
    van_routes, deferred_initial_customers, insertion_failure_reasons = (
        _build_initial_vans_for_container_routes(
            data,
            config,
            container_routes,
            warehouse_ready_time,
            van_home,
        )
    )
    retry_result = _retry_destinations_after_van_failure(
        data,
        config,
        destinations,
        deferred_initial_customers,
        van_home,
    )
    if retry_result is not None:
        (
            destinations,
            tractor_routes,
            container_routes,
            tractor_home,
            trailer_home,
            truck_route,
            warehouse_ready_time,
            van_routes,
            deferred_initial_customers,
            insertion_failure_reasons,
        ) = retry_result
    initial_timing["t_build_initial_van_routes"] = time.perf_counter() - stage_start
    selected_transshipment = int(
        next(iter(container_routes.values()))["destination_warehouse"]
        if container_routes
        else _select_transshipment(data, config)
    )
    drone_initial_carrier = config.build_drone_initial_carrier(data.transshipment_nodes)
    drone_home_warehouse = config.build_drone_home_warehouse(data.transshipment_nodes)
    primary_van = sorted(van_routes, key=lambda item: int(item.split("_")[1]))[0]
    van_route = van_routes[primary_van].copy()
    service_mode = {customer: "van" for customer in data.customers}
    order_assignment, container_assignment = _build_assignments(data, container_routes)
    state = TVDState(
        port_node=data.port_node,
        truck_depot_node=data.truck_depot_node,
        transshipment_nodes=data.transshipment_nodes.copy(),
        selected_transshipment=selected_transshipment,
        container_origin=data.container_origin,
        truck_route=truck_route,
        van_route=van_route,
        tractor_routes=tractor_routes,
        tractor_home=tractor_home,
        trailer_home=trailer_home,
        container_routes=container_routes,
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
            "warehouse_ready_time": warehouse_ready_time,
            "initial_solution_destinations": dict(destinations),
            "initial_solution_destination_retry": retry_result is not None,
            "initial_solution_insertion_failures": dict(insertion_failure_reasons),
            "selected_transshipment_legacy_alias": True,
        },
    )

    if deferred_initial_customers:
        state.unassigned = sorted(set(int(customer) for customer in deferred_initial_customers))
        fallback_failures: List[int] = []
        stage_start = time.perf_counter()
        for customer in list(state.unassigned):
            if (
                config.fleet.drone_enabled
                and data.drone_eligible.get(int(customer), False)
                and _apply_drone_sortie_for_customers(
                    state,
                    [int(customer)],
                    data,
                    config,
                    construction_unassigned=state.unassigned,
                )
            ):
                continue
            fallback_failures.append(int(customer))
            reason = insertion_failure_reasons.get(
                int(customer),
                f"customer {int(customer)} cannot be inserted without violating van capacity/time window.",
            )
            warnings.warn(
                "initial_solution could not assign customer "
                f"{int(customer)} after van insertion and drone fallback. {reason}",
                RuntimeWarning,
                stacklevel=2,
            )
        state.unassigned = sorted(set(fallback_failures))
        state.metadata["initial_solution_deferred_customers"] = sorted(
            set(deferred_initial_customers)
        )
        state.metadata["initial_solution_fallback_failures"] = state.unassigned.copy()
        initial_timing["t_initial_drone_fallback"] = (
            time.perf_counter() - stage_start
        )
    else:
        state.metadata["initial_solution_deferred_customers"] = []
        state.metadata["initial_solution_fallback_failures"] = []
        initial_timing["t_initial_drone_fallback"] = 0.0

    mandatory_drone_customers = [
        int(customer)
        for customer in data.customers
        if data.is_high_floor.get(customer, False)
        and data.drone_eligible.get(customer, False)
        and any(customer in route for route in state.van_routes.values())
    ]
    if mandatory_drone_customers:
        stage_start = time.perf_counter()
        fallback_failures: List[int] = []
        state.van_routes = _remove_customers_from_van_routes(
            state.van_routes, mandatory_drone_customers
        )
        state.sync_primary_van_route()
        for customer in mandatory_drone_customers:
            state.mark_unassigned(customer)
        for customer in mandatory_drone_customers:
            if _apply_drone_sortie_for_customers(
                state,
                [int(customer)],
                data,
                config,
                construction_unassigned=state.unassigned,
            ):
                continue
            fallback_failures.append(int(customer))
            warnings.warn(
                "initial_solution could not assign customer "
                f"{int(customer)} after van insertion and drone fallback.",
                RuntimeWarning,
                stacklevel=2,
            )
        if fallback_failures:
            state.metadata["initial_solution_fallback_failures"] = sorted(
                set(
                    state.metadata.get("initial_solution_fallback_failures", [])
                    + fallback_failures
                )
            )
        initial_timing["t_mandatory_high_floor_drone_repair"] = (
            time.perf_counter() - stage_start
        )
    else:
        initial_timing["t_mandatory_high_floor_drone_repair"] = 0.0

    stage_start = time.perf_counter()
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
        if (
            not data.is_high_floor.get(seed, False)
            and _van_saving_for_customers(state, sortie_customers, data, config)
            <= config.cost.drone_fixed_cost
        ):
            continue

        if not data.is_high_floor.get(seed, False):
            changed = True
            while changed:
                changed = False
                best_candidate = None
                best_distance = None
                for candidate in drone_candidates:
                    if data.is_high_floor.get(candidate, False):
                        continue
                    trial_customers = sortie_customers + [candidate]
                    if (
                        _van_saving_for_customers(state, trial_customers, data, config)
                        <= config.cost.drone_fixed_cost
                    ):
                        continue
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
    initial_timing["t_optional_drone_refinement"] = time.perf_counter() - stage_start

    mandatory_unserved = [
        int(customer)
        for customer, high_floor in data.is_high_floor.items()
        if high_floor and state.service_mode.get(customer) != "drone"
    ]
    if mandatory_unserved:
        state.van_routes = _remove_customers_from_van_routes(
            state.van_routes, mandatory_unserved
        )
        state.sync_primary_van_route()
        for customer in mandatory_unserved:
            state.mark_unassigned(customer)

    stage_start = time.perf_counter()
    objective(state, data, config)
    initial_timing["t_initial_final_objective"] = time.perf_counter() - stage_start
    stage_start = time.perf_counter()
    feasible, violations = check_solution_feasible(state, data, config)
    initial_timing["t_initial_final_feasibility"] = time.perf_counter() - stage_start
    initial_profile_end = snapshot_profile()
    state.metadata["initial_timing"] = initial_timing
    state.metadata["initial_state_copy_count"] = int(
        initial_profile_end.get("state_copy_calls", 0)
    ) - int(initial_profile_start.get("state_copy_calls", 0))
    state.metadata["initial_deepcopy_count"] = int(
        initial_profile_end.get("state_deepcopy_calls", 0)
    ) - int(initial_profile_start.get("state_deepcopy_calls", 0))
    if not feasible:
        insertion_failures = state.metadata.get("initial_solution_insertion_failures", {})
        root_causes: List[str] = []
        if isinstance(insertion_failures, dict):
            for customer in sorted(set(state.unassigned)):
                reason = insertion_failures.get(customer) or insertion_failures.get(str(customer))
                if reason:
                    root_causes.append(str(reason))
        message_parts = root_causes + list(violations)
        raise ValueError(
            "initial_solution could not construct a feasible solution: "
            + "; ".join(message_parts)
        )
    return state
