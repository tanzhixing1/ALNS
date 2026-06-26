from __future__ import annotations

from typing import Dict, List, Tuple

from config import TVDConfig
from dataset_loader import InstanceData
from state import TVDState


def sortie_nodes(sortie) -> Tuple[int, List[int], int]:
    """Return launch, ordered drone customers, and recovery for a sortie."""

    if isinstance(sortie, dict):
        customers = sortie.get("customers", [])
        return (
            int(sortie["launch"]),
            [int(customer) for customer in customers],
            int(sortie["recovery"]),
        )
    launch, customer, recovery = sortie
    return int(launch), [int(customer)], int(recovery)


def drone_sortie_distance(sortie, data: InstanceData) -> float:
    launch, customers, recovery = sortie_nodes(sortie)
    if not customers:
        return 0.0
    dist = data.drone_distance_matrix
    path = [launch] + customers + [recovery]
    return float(sum(dist[path[idx], path[idx + 1]] for idx in range(len(path) - 1)))


def _travel_minutes(distance: float, speed_kmph: float) -> float:
    return float(distance) / speed_kmph * 60.0


def _empty_timing() -> Dict[str, object]:
    return {
        "truck_arrival": {},
        "van_arrival": {},
        "drone_arrival": {},
        "service_start": {},
        "service_finish": {},
        "van_waiting_time": 0.0,
        "drone_waiting_time": 0.0,
        "early_waiting_time": 0.0,
        "time_window_violations": [],
        "truck_arrival_time": 0.0,
        "van_start_time": 0.0,
        "van_arrival_sequence": [],
    }


def _record_customer_service(
    timing: Dict[str, object],
    customer: int,
    arrival_time: float,
    data: InstanceData,
) -> float:
    violations = timing["time_window_violations"]
    time_window = data.time_windows.get(customer)
    service_time = data.service_times.get(customer)

    if time_window is None:
        violations.append(f"customer {customer} has no time_window.")
        earliest, latest = 0.0, float("inf")
    else:
        earliest, latest = time_window

    if service_time is None:
        violations.append(f"customer {customer} has no service_time.")
        service_time = 0.0

    early_wait = max(0.0, float(earliest) - arrival_time)
    service_start = max(arrival_time, float(earliest))
    service_finish = service_start + float(service_time)

    if service_start > float(latest) + 1e-9:
        violations.append(
            f"customer {customer} service_start {service_start:.3f} exceeds latest {float(latest):.3f}."
        )

    timing["early_waiting_time"] = float(timing["early_waiting_time"]) + early_wait
    timing["service_start"][customer] = float(service_start)
    timing["service_finish"][customer] = float(service_finish)
    return float(service_finish)


def compute_van_arrival_times(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> List[float]:
    timing = compute_timing(state, data, config)
    return [
        float(item["arrival_time"])
        for item in timing.get("van_arrival_sequence", [])
    ]


def _route_position(route: List[int], node: int, start: int = 0) -> int:
    for idx in range(start, len(route)):
        if route[idx] == node:
            return idx
    return -1


def compute_timing(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Dict[str, object]:
    """Propagate truck, van, and drone times in minutes.

    Distances are kilometers and speeds are kilometers/hour. Customer time
    windows are hard constraints: early arrivals wait until earliest, while
    late service starts are recorded as infeasible violations.
    """

    timing = _empty_timing()

    truck_time = 0.0
    truck_arrival: Dict[int, float] = timing["truck_arrival"]  # type: ignore[assignment]
    if state.truck_route:
        truck_arrival[int(state.truck_route[0])] = 0.0
    for idx in range(len(state.truck_route) - 1):
        pred = state.truck_route[idx]
        succ = state.truck_route[idx + 1]
        truck_time += _travel_minutes(
            data.ground_distance_matrix[pred, succ],
            config.fleet.tractor_speed_kmph,
        )
        truck_arrival[int(succ)] = float(truck_time)

    truck_arrival_time = truck_arrival.get(state.selected_transshipment, truck_time)
    timing["truck_arrival_time"] = float(truck_arrival_time)
    timing["van_start_time"] = float(truck_arrival_time)

    route = state.van_route
    route_positions: Dict[Tuple[int, int], int] = {}
    for idx, node in enumerate(route):
        route_positions[(idx, int(node))] = idx

    launch_sorties: Dict[int, List[dict]] = {}
    for sortie in state.drone_sorties:
        launch, _, recovery = sortie_nodes(sortie)
        launch_pos = _route_position(route, launch)
        recovery_pos = _route_position(route, recovery, launch_pos)
        if launch_pos >= 0 and recovery_pos >= launch_pos:
            launch_sorties.setdefault(launch_pos, []).append(sortie)

    pending_recoveries: Dict[int, List[Tuple[dict, float]]] = {}
    van_customers = set(state.get_van_customers())
    van_arrival: Dict[int, float] = timing["van_arrival"]  # type: ignore[assignment]
    drone_arrival: Dict[int, float] = timing["drone_arrival"]  # type: ignore[assignment]
    van_sequence: List[Dict[str, float]] = timing["van_arrival_sequence"]  # type: ignore[assignment]

    current_time = float(truck_arrival_time)
    for idx, node in enumerate(route):
        node = int(node)
        if idx > 0:
            pred = route[idx - 1]
            current_time += _travel_minutes(
                data.ground_distance_matrix[pred, node],
                config.fleet.van_speed_kmph,
            )

        arrival_time = float(current_time)
        van_arrival[node] = arrival_time
        van_sequence.append(
            {
                "route_index": float(idx),
                "node": float(node),
                "arrival_time": arrival_time,
            }
        )

        finish_time = arrival_time
        if node in van_customers:
            finish_time = _record_customer_service(timing, node, arrival_time, data)

        for sortie in launch_sorties.get(idx, []):
            launch, sortie_customers, recovery = sortie_nodes(sortie)
            recovery_pos = _route_position(route, recovery, idx)
            if recovery_pos < idx:
                continue

            launch_time = float(arrival_time)
            drone_time = launch_time
            prev = launch
            for customer in sortie_customers:
                drone_time += _travel_minutes(
                    data.drone_distance_matrix[prev, customer],
                    config.fleet.drone_speed_kmph,
                )
                drone_arrival[int(customer)] = float(drone_time)
                drone_time = _record_customer_service(
                    timing,
                    int(customer),
                    float(drone_time),
                    data,
                )
                prev = customer
            drone_time += _travel_minutes(
                data.drone_distance_matrix[prev, recovery],
                config.fleet.drone_speed_kmph,
            )
            pending_recoveries.setdefault(recovery_pos, []).append((sortie, float(drone_time)))
            if isinstance(sortie, dict):
                sortie["launch_time"] = launch_time
                sortie["recovery_time"] = float(drone_time)
                sortie["same_node"] = bool(launch == recovery)

        latest_departure = float(finish_time)
        for sortie, drone_recovery_time in pending_recoveries.get(idx, []):
            van_waiting = max(0.0, drone_recovery_time - arrival_time)
            drone_waiting = max(0.0, arrival_time - drone_recovery_time)
            timing["van_waiting_time"] = float(timing["van_waiting_time"]) + van_waiting
            timing["drone_waiting_time"] = float(timing["drone_waiting_time"]) + drone_waiting
            latest_departure = max(latest_departure, drone_recovery_time)
            if isinstance(sortie, dict):
                sortie["van_waiting_time"] = float(van_waiting)
                sortie["drone_waiting_time"] = float(drone_waiting)
                sortie["synchronized_recovery_time"] = float(
                    max(arrival_time, drone_recovery_time)
                )

        current_time = latest_departure

    state.timing = timing
    state.metadata["timing"] = timing
    return timing


def update_drone_sortie_timing(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Tuple[float, float]:
    """Fill launch/recovery timing and waiting fields in-place."""

    timing = compute_timing(state, data, config)
    return (
        float(timing.get("van_waiting_time", 0.0)),
        float(timing.get("drone_waiting_time", 0.0)),
    )


def compute_waiting_minutes(state: TVDState, data: InstanceData, config: TVDConfig) -> float:
    """Simplified synchronization waiting at recovery nodes."""

    van_waiting, drone_waiting = update_drone_sortie_timing(state, data, config)
    return van_waiting + drone_waiting


def check_solution_feasible(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Tuple[bool, List[str]]:
    violations: List[str] = []
    customers = set(data.customers)
    route = state.van_route

    if state.port_node != data.port_node:
        violations.append("state.port_node does not match instance port node.")
    if state.truck_depot_node != data.truck_depot_node:
        violations.append("state.truck_depot_node does not match instance truck depot.")
    if state.selected_transshipment not in state.transshipment_nodes:
        violations.append("selected_transshipment must be a candidate transshipment node.")
    if state.container_origin != data.port_node and state.container_origin not in state.transshipment_nodes:
        violations.append("container_origin must be the port or a candidate transshipment node.")

    expected_truck_route = (
        [state.truck_depot_node, state.selected_transshipment]
        if state.container_origin == state.selected_transshipment
        else [state.truck_depot_node, state.container_origin, state.selected_transshipment]
    )
    if state.truck_route != expected_truck_route:
        violations.append(
            f"truck_route must be {expected_truck_route} for the selected transshipment."
        )

    if len(route) < 2 or route[0] != state.selected_transshipment or route[-1] != state.selected_transshipment:
        violations.append("van_route must start and end at selected_transshipment.")

    illegal_route_nodes = [
        node for node in route if node not in customers and node != state.selected_transshipment
    ]
    if illegal_route_nodes:
        violations.append(f"van_route contains illegal nodes: {illegal_route_nodes}")

    van_customers = state.get_van_customers()
    drone_customers = state.get_drone_customers()
    all_served = van_customers + drone_customers

    for customer in data.customers:
        if customer not in state.order_assignment:
            violations.append(f"customer {customer} has no order_assignment.")

    for customer, assignment in state.order_assignment.items():
        if assignment.get("assigned_transshipment") != state.selected_transshipment:
            violations.append(
                f"order for customer {customer} is assigned to wrong transshipment."
            )
        if assignment.get("container_id") != 0:
            violations.append(f"order for customer {customer} must belong to container 0.")

    for container_id, assignment in state.container_assignment.items():
        if assignment.get("origin_node") != state.container_origin:
            violations.append(f"container {container_id} has wrong origin node.")
        if assignment.get("selected_transshipment") != state.selected_transshipment:
            violations.append(f"container {container_id} has wrong selected transshipment.")
        if assignment.get("candidate_transshipments") != state.transshipment_nodes:
            violations.append(f"container {container_id} has wrong candidate transshipments.")

    for customer in all_served:
        order = state.order_assignment.get(customer)
        if order is None:
            violations.append(f"served customer {customer} has no order_assignment.")
            continue
        container_id = order.get("container_id")
        container = state.container_assignment.get(container_id)
        if container is None:
            violations.append(f"customer {customer} belongs to missing container {container_id}.")
            continue
        if customer not in container.get("customers", []):
            violations.append(f"customer {customer} is not listed in container {container_id}.")

    duplicates = sorted({customer for customer in all_served if all_served.count(customer) > 1})
    if duplicates:
        violations.append(f"customers served more than once: {duplicates}")

    missing = sorted(customers - set(all_served) - set(state.unassigned))
    if missing:
        violations.append(f"customers missing from served/unassigned sets: {missing}")

    if state.unassigned:
        violations.append(f"unassigned customers remain: {sorted(state.unassigned)}")

    unexpected = sorted(set(all_served) - customers)
    if unexpected:
        violations.append(f"unexpected served customers: {unexpected}")

    if sum(data.demands[c] for c in van_customers) > config.fleet.van_capacity_kg:
        violations.append("van payload capacity exceeded.")

    timing = compute_timing(state, data, config)
    for customer in data.customers:
        if customer not in data.time_windows:
            violations.append(f"customer {customer} has no time_window.")
        if customer not in data.service_times:
            violations.append(f"customer {customer} has no service_time.")

    for customer in all_served:
        if customer not in timing.get("service_start", {}):
            violations.append(f"served customer {customer} has no service_start.")
            continue
        _, latest = data.time_windows.get(customer, (0.0, float("inf")))
        service_start = float(timing["service_start"][customer])
        if service_start > float(latest) + 1e-9:
            already_reported = any(
                f"customer {customer}" in str(violation) and "latest" in str(violation)
                for violation in timing.get("time_window_violations", [])
            )
            if not already_reported:
                violations.append(
                    f"customer {customer} violates time window: service_start {service_start:.3f} > latest {float(latest):.3f}."
                )

    for violation in timing.get("time_window_violations", []):
        if violation not in violations:
            violations.append(str(violation))

    van_start_time = float(timing.get("van_start_time", 0.0))
    truck_arrival_time = float(timing.get("truck_arrival_time", 0.0))
    if van_start_time + 1e-9 < truck_arrival_time:
        violations.append("van starts before the container arrives at selected_transshipment.")

    for sortie in state.drone_sorties:
        launch, sortie_customers, recovery = sortie_nodes(sortie)
        if not sortie_customers:
            violations.append(f"drone sortie has no customers: {sortie}")
        if not config.fleet.drone_enabled:
            violations.append("drone sortie exists while drone is disabled.")
        if launch not in route or recovery not in route:
            violations.append(f"drone launch/recovery not on van_route: {sortie}")
        else:
            launch_pos = _route_position(route, launch)
            recovery_pos = _route_position(route, recovery, launch_pos)
            if recovery_pos < launch_pos:
                violations.append(f"drone recovery occurs before launch on van_route: {sortie}")
        for customer in sortie_customers:
            if customer not in customers:
                violations.append(f"drone sortie has illegal customer: {sortie}")
                continue
            if customer in van_customers:
                violations.append(f"drone customer {customer} also appears in van_route.")
            if not data.drone_eligible.get(customer, False):
                violations.append(f"customer {customer} is not drone eligible.")
        payload = sum(data.demands.get(customer, 0.0) for customer in sortie_customers)
        if payload > config.fleet.drone_capacity_kg:
            violations.append(f"drone payload exceeded for sortie {sortie}.")
        if drone_sortie_distance(sortie, data) > config.fleet.drone_endurance_km:
            violations.append(f"drone endurance exceeded for sortie {sortie}.")
        if isinstance(sortie, dict):
            if sortie.get("van_waiting_time", 0.0) < 0:
                violations.append(f"negative van waiting time in sortie: {sortie}")
            if sortie.get("drone_waiting_time", 0.0) < 0:
                violations.append(f"negative drone waiting time in sortie: {sortie}")

    if float(timing.get("van_waiting_time", 0.0)) < -1e-9:
        violations.append("total van waiting time is negative.")
    if float(timing.get("drone_waiting_time", 0.0)) < -1e-9:
        violations.append("total drone waiting time is negative.")

    if config.fleet.drone_enabled:
        for customer, high_floor in data.is_high_floor.items():
            if high_floor and state.service_mode.get(customer) != "drone":
                violations.append(f"high-floor customer {customer} must be served by drone.")

    return len(violations) == 0, violations
