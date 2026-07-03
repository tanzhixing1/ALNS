from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from config import TVDConfig
from dataset_loader import InstanceData
from state import TVDState
from alns_profile import get_cache, increment, set_cache


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


def delivery_demand(data: InstanceData, customer: int) -> float:
    return float(data.demands.get(customer, 0.0))


def pickup_demand(data: InstanceData, customer: int) -> float:
    return float(getattr(data, "pickup_demands", {}).get(customer, 0.0))


def drone_sortie_energy_details(
    sortie, data: InstanceData, config: TVDConfig
) -> Tuple[float, List[Dict[str, float]]]:
    """Compute payload-dependent drone energy for a delivery-only sortie.

    Energy increment follows the paper form
    [beta1 * (P + D + m) + beta0] * tau. The current prototype has no pickup
    demand yet, so P is zero and D is the remaining delivery payload.
    """

    launch, customers, recovery = sortie_nodes(sortie)
    route = [launch] + customers + [recovery]
    remaining_delivery = float(sum(delivery_demand(data, customer) for customer in customers))
    pickup_load = 0.0
    cumulative = 0.0
    rows: List[Dict[str, float]] = []

    for idx in range(len(route) - 1):
        start = route[idx]
        end = route[idx + 1]
        distance = float(data.drone_distance_matrix[start, end])
        flight_hours = distance / config.fleet.drone_speed_kmph
        payload_departure = pickup_load + remaining_delivery
        effective_weight = payload_departure + config.fleet.drone_self_weight_kg
        power = (
            config.fleet.drone_payload_energy_coeff * effective_weight
            + config.fleet.drone_base_energy_coeff
        )
        energy = power * flight_hours
        cumulative += energy
        delivered = delivery_demand(data, end) if end in customers else 0.0
        picked_up = pickup_demand(data, end) if end in customers else 0.0
        delivery_after_service = remaining_delivery - delivered
        pickup_after_service = pickup_load + picked_up
        rows.append(
            {
                "from": float(start),
                "to": float(end),
                "distance": distance,
                "flight_hours": flight_hours,
                "delivery_load_departure": remaining_delivery,
                "pickup_load_departure": pickup_load,
                "payload_departure": payload_departure,
                "effective_weight": effective_weight,
                "energy_increment": energy,
                "cumulative_energy": cumulative,
                "delivered_at_to": delivered,
                "picked_up_at_to": picked_up,
                "delivery_load_after_service": delivery_after_service,
                "pickup_load_after_service": pickup_after_service,
                "payload_after_service": delivery_after_service + pickup_after_service,
            }
        )
        remaining_delivery = delivery_after_service
        pickup_load = pickup_after_service

    return float(cumulative), rows


def drone_sortie_energy(sortie, data: InstanceData, config: TVDConfig) -> float:
    total, _ = drone_sortie_energy_details(sortie, data, config)
    return total


def drone_sortie_peak_payload(sortie, data: InstanceData, config: TVDConfig) -> float:
    _, rows = drone_sortie_energy_details(sortie, data, config)
    peak = 0.0
    for row in rows:
        peak = max(
            peak,
            float(row["payload_departure"]),
            float(row["payload_after_service"]),
        )
    return peak


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
        "drone_physical_routes": {},
        "drone_physical_sorties": {},
        "drone_warehouse_launch_count": {},
        "drone_warehouse_return_count": {},
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


def _sortie_position_hint(sortie, field: str) -> Optional[int]:
    if not isinstance(sortie, dict) or sortie.get(field) is None:
        return None
    try:
        return int(sortie[field])
    except (TypeError, ValueError):
        return None


def _resolve_sortie_positions(sortie, route: List[int]) -> Tuple[int, int]:
    """Resolve launch/recovery positions, preserving repeated warehouse nodes."""

    launch, _, recovery = sortie_nodes(sortie)
    launch_hint = _sortie_position_hint(sortie, "launch_position")
    recovery_hint = _sortie_position_hint(sortie, "recovery_position")

    launch_pos = -1
    if (
        launch_hint is not None
        and 0 <= launch_hint < len(route)
        and int(route[launch_hint]) == launch
    ):
        launch_pos = launch_hint
    else:
        launch_pos = _route_position(route, launch)

    recovery_pos = -1
    if (
        recovery_hint is not None
        and 0 <= recovery_hint < len(route)
        and int(route[recovery_hint]) == recovery
        and recovery_hint >= launch_pos
    ):
        recovery_pos = recovery_hint
    elif launch_pos >= 0:
        recovery_pos = _route_position(route, recovery, launch_pos)

    return launch_pos, recovery_pos


def _write_sortie_positions(sortie, launch_pos: int, recovery_pos: int) -> None:
    if isinstance(sortie, dict):
        sortie["launch_position"] = int(launch_pos)
        sortie["recovery_position"] = int(recovery_pos)


def _is_warehouse_node(state: TVDState, node: int) -> bool:
    return int(node) == int(state.selected_transshipment) or int(node) in {
        int(item) for item in state.transshipment_nodes
    }


def _sorties_by_position(state: TVDState, route: List[int]) -> Tuple[Dict[int, List[dict]], Dict[int, List[dict]]]:
    launches: Dict[int, List[dict]] = {}
    recoveries: Dict[int, List[dict]] = {}
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        launch_pos, recovery_pos = _resolve_sortie_positions(sortie, route)
        if launch_pos >= 0:
            launches.setdefault(launch_pos, []).append(sortie)
        if recovery_pos >= 0:
            recoveries.setdefault(recovery_pos, []).append(sortie)
    return launches, recoveries


def _van_load_trace(state: TVDState, data: InstanceData) -> Tuple[List[Dict[str, float]], float]:
    route = state.van_route
    van_customers = set(state.get_van_customers())
    launches, recoveries = _sorties_by_position(state, route)
    delivery_load = float(
        sum(delivery_demand(data, customer) for customer in state.get_served_customers())
    )
    pickup_load = 0.0
    peak_payload = delivery_load + pickup_load
    trace: List[Dict[str, float]] = []

    for route_index, node in enumerate(route):
        node = int(node)
        delivery_arrival = delivery_load
        pickup_arrival = pickup_load

        delivered_here = delivery_demand(data, node) if node in van_customers else 0.0
        picked_up_here = pickup_demand(data, node) if node in van_customers else 0.0
        delivery_load -= delivered_here
        pickup_load += picked_up_here

        launched_delivery = 0.0
        for sortie in launches.get(route_index, []):
            _, customers, _ = sortie_nodes(sortie)
            launched_delivery += sum(delivery_demand(data, customer) for customer in customers)
        delivery_load -= launched_delivery

        recovered_pickup = 0.0
        for sortie in recoveries.get(route_index, []):
            _, customers, _ = sortie_nodes(sortie)
            recovered_pickup += sum(pickup_demand(data, customer) for customer in customers)
        pickup_load += recovered_pickup

        peak_payload = max(peak_payload, delivery_load + pickup_load)
        trace.append(
            {
                "route_index": float(route_index),
                "node": float(node),
                "delivery_load_arrival": float(delivery_arrival),
                "pickup_load_arrival": float(pickup_arrival),
                "delivered_here": float(delivered_here),
                "picked_up_here": float(picked_up_here),
                "launched_delivery": float(launched_delivery),
                "recovered_pickup": float(recovered_pickup),
                "delivery_load_departure": float(delivery_load),
                "pickup_load_departure": float(pickup_load),
                "payload_departure": float(delivery_load + pickup_load),
            }
        )

    return trace, float(peak_payload)


def compute_timing(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Dict[str, object]:
    """Propagate truck, van, and drone times in minutes.

    Distances are kilometers and speeds are kilometers/hour. Customer time
    windows are hard constraints: early arrivals wait until earliest, while
    late service starts are recorded as infeasible violations.
    """

    increment("compute_timing_calls")
    signature = state.cache_signature()
    cached = get_cache("timing", state, signature)
    if cached is not None:
        increment("compute_timing_cache_hits")
        state.timing = cached
        state.metadata["timing"] = cached
        return cached

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

    launch_sorties: Dict[int, List[dict]] = {}
    for sortie in state.drone_sorties:
        launch, _, recovery = sortie_nodes(sortie)
        launch_pos, recovery_pos = _resolve_sortie_positions(sortie, route)
        if launch_pos >= 0 and recovery_pos >= launch_pos:
            _write_sortie_positions(sortie, launch_pos, recovery_pos)
            launch_sorties.setdefault(launch_pos, []).append(sortie)

    pending_recoveries: Dict[int, List[Tuple[dict, int, float]]] = {}
    van_customers = set(state.get_van_customers())
    van_arrival: Dict[int, float] = timing["van_arrival"]  # type: ignore[assignment]
    drone_arrival: Dict[int, float] = timing["drone_arrival"]  # type: ignore[assignment]
    van_sequence: List[Dict[str, float]] = timing["van_arrival_sequence"]  # type: ignore[assignment]
    physical_routes: Dict[int, List[int]] = timing["drone_physical_routes"]  # type: ignore[assignment]
    physical_sorties: Dict[int, List[Dict[str, object]]] = timing["drone_physical_sorties"]  # type: ignore[assignment]
    warehouse_launch_count: Dict[int, int] = timing["drone_warehouse_launch_count"]  # type: ignore[assignment]
    warehouse_return_count: Dict[int, int] = timing["drone_warehouse_return_count"]  # type: ignore[assignment]
    available_drones: List[Tuple[int, int]] = []
    next_drone_id = 1

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

        latest_departure = float(finish_time)
        for sortie, drone_id, drone_recovery_time in pending_recoveries.get(idx, []):
            van_waiting = max(0.0, drone_recovery_time - latest_departure)
            drone_waiting = max(0.0, latest_departure - drone_recovery_time)
            timing["van_waiting_time"] = float(timing["van_waiting_time"]) + van_waiting
            timing["drone_waiting_time"] = float(timing["drone_waiting_time"]) + drone_waiting
            latest_departure = max(latest_departure, drone_recovery_time)
            recovery_node = sortie_nodes(sortie)[2]
            if not _is_warehouse_node(state, recovery_node):
                candidate = (drone_id, idx)
                if candidate not in available_drones:
                    available_drones.append(candidate)
            if isinstance(sortie, dict):
                sortie["van_waiting_time"] = float(van_waiting)
                sortie["drone_waiting_time"] = float(drone_waiting)
                sortie["synchronized_recovery_time"] = float(latest_departure)

        for sortie in launch_sorties.get(idx, []):
            launch, sortie_customers, recovery = sortie_nodes(sortie)
            launch_pos, recovery_pos = _resolve_sortie_positions(sortie, route)
            _write_sortie_positions(sortie, launch_pos, recovery_pos)
            if recovery_pos < idx:
                continue

            reusable_idx = next(
                (
                    pos
                    for pos, (_, available_pos) in enumerate(available_drones)
                    if available_pos <= idx
                ),
                None,
            )
            if reusable_idx is not None:
                drone_id, _ = available_drones.pop(reusable_idx)
            else:
                drone_id = next_drone_id
                next_drone_id += 1
                physical_routes[drone_id] = [int(route[0])]
                physical_sorties[drone_id] = []
                warehouse_launch_count[drone_id] = 1
                warehouse_return_count[drone_id] = 0

            launch_time = float(latest_departure)
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
            if recovery_pos != idx:
                pending_recoveries.setdefault(recovery_pos, []).append((sortie, drone_id, float(drone_time)))
            if _is_warehouse_node(state, recovery):
                warehouse_return_count[drone_id] = warehouse_return_count.get(drone_id, 0) + 1
            physical_route = physical_routes.setdefault(drone_id, [launch])
            if not physical_route or int(physical_route[-1]) != int(launch):
                physical_route.append(int(launch))
            physical_route.extend(sortie_customers + [recovery])
            physical_sorties.setdefault(drone_id, []).append(
                {
                    "launch_node": int(launch),
                    "launch_position": int(idx),
                    "recovery_node": int(recovery),
                    "recovery_position": int(recovery_pos),
                    "customers": [int(customer) for customer in sortie_customers],
                    "launch_time": float(launch_time),
                    "recovery_time": float(drone_time),
                }
            )
            if isinstance(sortie, dict):
                sortie["drone_id"] = drone_id
                sortie["launch_time"] = launch_time
                sortie["recovery_time"] = float(drone_time)
                sortie["same_node"] = bool(launch == recovery)

            if recovery_pos == idx:
                van_waiting = max(0.0, drone_time - latest_departure)
                drone_waiting = max(0.0, latest_departure - drone_time)
                timing["van_waiting_time"] = float(timing["van_waiting_time"]) + van_waiting
                timing["drone_waiting_time"] = float(timing["drone_waiting_time"]) + drone_waiting
                latest_departure = max(latest_departure, drone_time)
                if not _is_warehouse_node(state, recovery):
                    candidate = (drone_id, idx)
                    if candidate not in available_drones:
                        available_drones.append(candidate)
                if isinstance(sortie, dict):
                    sortie["van_waiting_time"] = float(van_waiting)
                    sortie["drone_waiting_time"] = float(drone_waiting)
                    sortie["synchronized_recovery_time"] = float(latest_departure)

        current_time = latest_departure

    if route and route[-1] in state.transshipment_nodes:
        terminal_warehouse = int(route[-1])
        for drone_id, _ in available_drones:
            physical_route = physical_routes.setdefault(drone_id, [])
            if not physical_route or int(physical_route[-1]) != terminal_warehouse:
                physical_route.append(terminal_warehouse)
                warehouse_return_count[drone_id] = warehouse_return_count.get(drone_id, 0) + 1

    state.timing = timing
    state.metadata["timing"] = timing
    set_cache("timing", state, signature, timing)
    return timing


def _active_van_routes(state: TVDState) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    return {
        str(van_id): [int(node) for node in route]
        for van_id, route in routes.items()
        if len(route) >= 2
    }


def _van_id_sort_key(van_id: str) -> int:
    try:
        return int(str(van_id).split("_")[1])
    except (IndexError, ValueError):
        return 0


def _drone_id_sort_key(drone_id: str) -> int:
    try:
        return int(str(drone_id).split("_")[1])
    except (IndexError, ValueError):
        return 0


def _sortie_van_id(sortie, field: str, fallback: str = "van_0") -> str:
    if isinstance(sortie, dict) and sortie.get(field):
        return str(sortie[field])
    return fallback


def _sortie_drone_id(sortie, fallback: str = "") -> str:
    if isinstance(sortie, dict) and sortie.get("drone_id") not in (None, ""):
        return str(sortie["drone_id"])
    return fallback


def _van_route_load_trace(
    route: List[int],
    van_id: str,
    state: TVDState,
    data: InstanceData,
) -> Tuple[List[Dict[str, float]], float]:
    van_customers = {
        int(node)
        for node in route
        if int(node) in data.customers and state.service_mode.get(int(node)) == "van"
    }
    launches: Dict[int, List[dict]] = {}
    recoveries: Dict[int, List[dict]] = {}
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        launch_van = _sortie_van_id(sortie, "launch_van_id", van_id)
        recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
        launch, _, recovery = sortie_nodes(sortie)
        if launch_van == van_id:
            launch_pos = _route_position(route, launch)
            if launch_pos >= 0:
                launches.setdefault(launch_pos, []).append(sortie)
        if recovery_van == van_id:
            recovery_pos = _route_position(route, recovery)
            if recovery_pos >= 0:
                recoveries.setdefault(recovery_pos, []).append(sortie)

    served_by_this_van = set(van_customers)
    for sorties in launches.values():
        for sortie in sorties:
            _, customers, _ = sortie_nodes(sortie)
            served_by_this_van.update(customers)

    delivery_load = float(sum(delivery_demand(data, customer) for customer in served_by_this_van))
    pickup_load = 0.0
    peak_payload = delivery_load
    trace: List[Dict[str, float]] = []

    for route_index, node in enumerate(route):
        node = int(node)
        delivery_arrival = delivery_load
        pickup_arrival = pickup_load
        delivered_here = delivery_demand(data, node) if node in van_customers else 0.0
        picked_up_here = pickup_demand(data, node) if node in van_customers else 0.0
        delivery_load -= delivered_here
        pickup_load += picked_up_here

        launched_delivery = 0.0
        for sortie in launches.get(route_index, []):
            _, customers, _ = sortie_nodes(sortie)
            launched_delivery += sum(delivery_demand(data, customer) for customer in customers)
        delivery_load -= launched_delivery

        recovered_pickup = 0.0
        for sortie in recoveries.get(route_index, []):
            _, customers, _ = sortie_nodes(sortie)
            recovered_pickup += sum(pickup_demand(data, customer) for customer in customers)
        pickup_load += recovered_pickup

        peak_payload = max(peak_payload, delivery_load + pickup_load)
        trace.append(
            {
                "route_index": float(route_index),
                "node": float(node),
                "delivery_load_arrival": float(delivery_arrival),
                "pickup_load_arrival": float(pickup_arrival),
                "delivered_here": float(delivered_here),
                "picked_up_here": float(picked_up_here),
                "launched_delivery": float(launched_delivery),
                "recovered_pickup": float(recovered_pickup),
                "delivery_load_departure": float(delivery_load),
                "pickup_load_departure": float(pickup_load),
                "payload_departure": float(delivery_load + pickup_load),
            }
        )

    return trace, float(peak_payload)


def _van_load_trace(state: TVDState, data: InstanceData) -> Tuple[List[Dict[str, float]], float]:
    rows: List[Dict[str, float]] = []
    peak = 0.0
    for van_id, route in _active_van_routes(state).items():
        van_rows, van_peak = _van_route_load_trace(route, van_id, state, data)
        for row in van_rows:
            row["van_id_sort"] = float(_van_id_sort_key(van_id))
            rows.append(row)
        peak = max(peak, van_peak)
    return rows, float(peak)


def compute_timing(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Dict[str, object]:
    increment("compute_timing_calls")
    signature = state.cache_signature()
    cached = get_cache("timing", state, signature)
    if cached is not None:
        increment("compute_timing_cache_hits")
        state.timing = cached
        state.metadata["timing"] = cached
        return cached

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
    warehouse_ready_time = {
        int(warehouse): float(ready_time)
        for warehouse, ready_time in state.metadata.get("warehouse_ready_time", {}).items()
    }
    for container in getattr(state, "container_routes", {}).values():
        if not isinstance(container, dict):
            continue
        warehouse = int(container.get("destination_warehouse", state.selected_transshipment))
        warehouse_ready_time[warehouse] = max(
            warehouse_ready_time.get(warehouse, 0.0),
            float(container.get("unload_complete", 0.0)),
        )
    timing["warehouse_ready_time"] = warehouse_ready_time
    timing["van_start_time"] = float(
        warehouse_ready_time.get(int(state.selected_transshipment), truck_arrival_time)
    )

    routes = _active_van_routes(state)
    sorted_route_items = sorted(routes.items(), key=lambda item: _van_id_sort_key(item[0]))
    van_start_time_by_van = {
        van_id: float(warehouse_ready_time.get(int(route[0]), truck_arrival_time))
        for van_id, route in sorted_route_items
        if route
    }
    timing["van_start_time_by_van"] = van_start_time_by_van

    def _service_finish_without_record(customer: int, arrival_time: float) -> float:
        earliest, _ = data.time_windows.get(customer, (0.0, float("inf")))
        service_time = data.service_times.get(customer, 0.0)
        return float(max(arrival_time, float(earliest)) + float(service_time))

    def _position_for_sortie(sortie: dict, route: List[int], node: int, field: str) -> int:
        hint = _sortie_position_hint(sortie, field)
        if hint is not None and 0 <= hint < len(route) and int(route[hint]) == int(node):
            return int(hint)
        return _route_position(route, int(node))

    sortie_specs: List[Dict[str, object]] = []
    for sortie_idx, sortie in enumerate(state.drone_sorties):
        if not isinstance(sortie, dict):
            continue
        launch, _, recovery = sortie_nodes(sortie)
        launch_van = _sortie_van_id(sortie, "launch_van_id", sorted(routes)[0] if routes else "van_0")
        recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
        if launch_van not in routes or recovery_van not in routes:
            continue
        launch_pos = _position_for_sortie(sortie, routes[launch_van], launch, "launch_position")
        recovery_pos = _position_for_sortie(sortie, routes[recovery_van], recovery, "recovery_position")
        if launch_pos >= 0 and recovery_pos >= 0:
            sortie["launch_position"] = int(launch_pos)
            sortie["recovery_position"] = int(recovery_pos)
            sortie_specs.append(
                {
                    "sortie_idx": sortie_idx,
                    "sortie": sortie,
                    "launch_van": launch_van,
                    "launch_pos": int(launch_pos),
                    "recovery_van": recovery_van,
                    "recovery_pos": int(recovery_pos),
                }
            )

    initial_by_van: Dict[str, List[str]] = {}
    for drone_id, van_id in state.drone_initial_carrier.items():
        initial_by_van.setdefault(str(van_id), []).append(str(drone_id))
    for drones in initial_by_van.values():
        drones.sort(key=_drone_id_sort_key)

    RecoveryEvents = Dict[Tuple[str, int, int], float]
    Timeline = Dict[str, List[Dict[str, float]]]

    def _position_recovery_wait(
        recovery_events: RecoveryEvents,
        van_id: str,
        position: int,
        exclude_sortie_idx: Optional[int] = None,
        exclude_sortie_idxs: Optional[List[int]] = None,
    ) -> float:
        wait_until = 0.0
        excluded = set(exclude_sortie_idxs or [])
        if exclude_sortie_idx is not None:
            excluded.add(int(exclude_sortie_idx))
        for (event_van, event_pos, event_sortie_idx), event_time in recovery_events.items():
            if event_van != van_id or int(event_pos) != int(position):
                continue
            if int(event_sortie_idx) in excluded:
                continue
            wait_until = max(wait_until, float(event_time))
        return float(wait_until)

    def _build_van_timelines(
        recovery_events: RecoveryEvents,
        record_services: bool,
        target_timing: Optional[Dict[str, object]] = None,
    ) -> Tuple[Dict[str, Dict[int, float]], Timeline]:
        van_arrivals: Dict[str, Dict[int, float]] = {}
        van_sequences: Timeline = {}
        for van_id, route in sorted_route_items:
            current_time = float(van_start_time_by_van.get(van_id, truck_arrival_time))
            van_arrivals[van_id] = {}
            van_sequences[van_id] = []
            for idx, node in enumerate(route):
                node = int(node)
                if idx > 0:
                    pred = int(route[idx - 1])
                    current_time += _travel_minutes(
                        data.ground_distance_matrix[pred, node],
                        config.fleet.van_speed_kmph,
                    )

                arrival_time = float(current_time)
                if node in data.customers and state.service_mode.get(node) == "van":
                    if record_services and target_timing is not None:
                        service_finish_time = _record_customer_service(
                            target_timing, node, arrival_time, data
                        )
                    else:
                        service_finish_time = _service_finish_without_record(node, arrival_time)
                    service_start_time = service_finish_time - float(data.service_times.get(node, 0.0))
                else:
                    service_start_time = arrival_time
                    service_finish_time = arrival_time

                recovery_wait_until = _position_recovery_wait(recovery_events, van_id, idx)
                departure_time = max(float(service_finish_time), float(recovery_wait_until))
                van_arrivals[van_id][node] = arrival_time
                van_sequences[van_id].append(
                    {
                        "route_index": float(idx),
                        "node": float(node),
                        "arrival_time": arrival_time,
                        "service_start_time": float(service_start_time),
                        "service_finish_time": float(service_finish_time),
                        "departure_time": float(departure_time),
                    }
                )
                current_time = float(departure_time)
        return van_arrivals, van_sequences

    def _compute_sortie_events(
        van_sequences: Timeline,
        recovery_events: RecoveryEvents,
        record_results: bool,
        target_timing: Optional[Dict[str, object]] = None,
    ) -> RecoveryEvents:
        new_events: RecoveryEvents = {}
        drone_location: Dict[str, str] = {
            str(drone_id): str(van_id)
            for drone_id, van_id in state.drone_initial_carrier.items()
        }
        drone_available_time: Dict[str, float] = {
            str(drone_id): float(
                van_start_time_by_van.get(str(van_id), truck_arrival_time)
            )
            for drone_id, van_id in state.drone_initial_carrier.items()
        }
        launch_records: List[Tuple[float, int, int, int, Dict[str, object]]] = []
        for spec in sortie_specs:
            launch_van = str(spec["launch_van"])
            launch_pos = int(spec["launch_pos"])
            sortie_idx = int(spec["sortie_idx"])
            same_anchor_sortie_idxs = [
                int(other["sortie_idx"])
                for other in sortie_specs
                if str(other["launch_van"]) == launch_van
                and int(other["launch_pos"]) == launch_pos
            ]
            entry = van_sequences[launch_van][launch_pos]
            node_ready_time = max(
                float(entry["service_finish_time"]),
                _position_recovery_wait(
                    recovery_events,
                    launch_van,
                    launch_pos,
                    exclude_sortie_idxs=same_anchor_sortie_idxs,
                ),
            )
            launch_records.append(
                (
                    float(node_ready_time),
                    _van_id_sort_key(launch_van),
                    launch_pos,
                    sortie_idx,
                    spec,
                )
            )
        launch_records.sort(key=lambda item: (item[0], item[1], item[2], item[3]))

        physical_routes: Dict[str, List[int]] = {}
        physical_sorties: Dict[str, List[Dict[str, object]]] = {}
        warehouse_launch_count: Dict[str, int] = {}
        warehouse_return_count: Dict[str, int] = {}
        drone_arrival: Dict[int, float] = (
            target_timing["drone_arrival"] if target_timing is not None else {}
        )  # type: ignore[assignment]

        for node_ready_time, _, _, sortie_idx, spec in launch_records:
            sortie = spec["sortie"]
            if not isinstance(sortie, dict):
                continue
            launch, sortie_customers, recovery = sortie_nodes(sortie)
            launch_van = str(spec["launch_van"])
            launch_pos = int(spec["launch_pos"])
            recovery_van = str(spec["recovery_van"])
            recovery_pos = int(spec["recovery_pos"])
            requested_drone_id = _sortie_drone_id(sortie)
            same_van_drones = [
                drone_id
                for drone_id in sorted(drone_location, key=_drone_id_sort_key)
                if drone_location.get(drone_id) == launch_van
            ]
            ready_drones = [
                drone_id
                for drone_id in same_van_drones
                if drone_available_time.get(drone_id, 0.0) <= node_ready_time + 1e-9
            ]
            if requested_drone_id in ready_drones:
                drone_id = requested_drone_id
            elif ready_drones:
                drone_id = ready_drones[0]
            elif requested_drone_id in same_van_drones:
                drone_id = requested_drone_id
            elif same_van_drones:
                drone_id = same_van_drones[0]
            else:
                drone_id = requested_drone_id or f"missing_drone_for_{launch_van}"

            launch_time = max(
                float(node_ready_time),
                float(drone_available_time.get(drone_id, node_ready_time)),
            )
            drone_time = float(launch_time)
            prev = launch
            for customer in sortie_customers:
                drone_time += _travel_minutes(
                    data.drone_distance_matrix[prev, customer],
                    config.fleet.drone_speed_kmph,
                )
                drone_arrival[int(customer)] = float(drone_time)
                if record_results and target_timing is not None:
                    drone_time = _record_customer_service(
                        target_timing,
                        int(customer),
                        float(drone_time),
                        data,
                    )
                else:
                    drone_time = _service_finish_without_record(int(customer), float(drone_time))
                prev = customer
            drone_time += _travel_minutes(
                data.drone_distance_matrix[prev, recovery],
                config.fleet.drone_speed_kmph,
            )

            recovery_entry = van_sequences[recovery_van][recovery_pos]
            recovery_arrival = float(recovery_entry["arrival_time"])
            synchronized_recovery_time = max(float(drone_time), recovery_arrival)
            new_events[(recovery_van, recovery_pos, sortie_idx)] = float(
                synchronized_recovery_time
            )
            van_waiting = max(0.0, float(drone_time) - recovery_arrival)
            drone_waiting = max(0.0, recovery_arrival - float(drone_time))
            drone_location[drone_id] = recovery_van
            drone_available_time[drone_id] = float(synchronized_recovery_time)

            if record_results and target_timing is not None:
                target_timing["van_waiting_time"] = (
                    float(target_timing["van_waiting_time"]) + van_waiting
                )
                target_timing["drone_waiting_time"] = (
                    float(target_timing["drone_waiting_time"]) + drone_waiting
                )
                physical_route = physical_routes.setdefault(
                    drone_id,
                    [int(state.van_home.get(launch_van, routes[launch_van][0]))],
                )
                if not physical_route or int(physical_route[-1]) != int(launch):
                    physical_route.append(int(launch))
                physical_route.extend(
                    [int(customer) for customer in sortie_customers] + [int(recovery)]
                )
                if _is_warehouse_node(state, launch):
                    warehouse_launch_count[drone_id] = warehouse_launch_count.get(drone_id, 0) + 1
                if _is_warehouse_node(state, recovery):
                    warehouse_return_count[drone_id] = warehouse_return_count.get(drone_id, 0) + 1
                physical_sorties.setdefault(drone_id, []).append(
                    {
                        "launch_node": int(launch),
                        "launch_van_id": launch_van,
                        "launch_position": int(launch_pos),
                        "recovery_node": int(recovery),
                        "recovery_van_id": recovery_van,
                        "recovery_position": int(recovery_pos),
                        "customers": [int(customer) for customer in sortie_customers],
                        "launch_time": float(launch_time),
                        "drone_arrival_time": float(drone_time),
                        "recovery_time": float(synchronized_recovery_time),
                    }
                )
                sortie["drone_id"] = drone_id
                sortie["launch_van_id"] = launch_van
                sortie["recovery_van_id"] = recovery_van
                sortie["launch_position"] = int(launch_pos)
                sortie["recovery_position"] = int(recovery_pos)
                sortie["launch_time"] = float(launch_time)
                sortie["drone_arrival_time"] = float(drone_time)
                sortie["recovery_time"] = float(synchronized_recovery_time)
                sortie["van_waiting_time"] = float(van_waiting)
                sortie["drone_waiting_time"] = float(drone_waiting)
                sortie["same_node"] = bool(launch == recovery)
                sortie["synchronized_recovery_time"] = float(synchronized_recovery_time)

        if record_results and target_timing is not None:
            target_timing["drone_physical_routes"] = physical_routes
            target_timing["drone_physical_sorties"] = physical_sorties
            target_timing["drone_warehouse_launch_count"] = warehouse_launch_count
            target_timing["drone_warehouse_return_count"] = warehouse_return_count
        return new_events

    def _events_close(left: RecoveryEvents, right: RecoveryEvents) -> bool:
        if set(left) != set(right):
            return False
        return all(abs(float(left[key]) - float(right[key])) <= 1e-7 for key in left)

    max_iterations = max(10, 2 * (sum(len(route) for route in routes.values()) + len(sortie_specs) + 1))
    recovery_events: RecoveryEvents = {}
    converged = False
    iterations_used = 0
    for iteration in range(1, max_iterations + 1):
        _, iteration_sequences = _build_van_timelines(
            recovery_events,
            record_services=False,
        )
        next_events = _compute_sortie_events(
            iteration_sequences,
            recovery_events,
            record_results=False,
        )
        iterations_used = iteration
        if _events_close(recovery_events, next_events):
            recovery_events = next_events
            converged = True
            break
        recovery_events = next_events

    van_arrival_by_van, van_sequence_by_van = _build_van_timelines(
        recovery_events,
        record_services=True,
        target_timing=timing,
    )
    final_events = _compute_sortie_events(
        van_sequence_by_van,
        recovery_events,
        record_results=True,
        target_timing=timing,
    )
    if not converged or not _events_close(recovery_events, final_events):
        timing["time_window_violations"].append(
            f"timing fixed-point did not converge within {max_iterations} iterations."
        )
    timing["timing_scheduler"] = "fixed-point"
    timing["timing_iterations"] = int(iterations_used)
    timing["recovery_events_by_van_position"] = {
        f"{van_id}:{position}:{sortie_idx}": float(event_time)
        for (van_id, position, sortie_idx), event_time in final_events.items()
    }

    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        recovery_van = _sortie_van_id(sortie, "recovery_van_id")
        recovery_pos = int(sortie.get("recovery_position", -1))
        recovery_time = float(sortie.get("recovery_time", 0.0))
        sequence = van_sequence_by_van.get(recovery_van, [])
        if 0 <= recovery_pos < len(sequence):
            departure_time = float(sequence[recovery_pos]["departure_time"])
            if departure_time + 1e-9 < recovery_time:
                timing["time_window_violations"].append(
                    f"{recovery_van} departs position {recovery_pos} before recovery_time {recovery_time:.3f}."
                )
            if recovery_pos + 1 < len(sequence):
                current_node = int(sequence[recovery_pos]["node"])
                next_node = int(sequence[recovery_pos + 1]["node"])
                next_arrival = float(sequence[recovery_pos + 1]["arrival_time"])
                required_arrival = recovery_time + _travel_minutes(
                    data.ground_distance_matrix[current_node, next_node],
                    config.fleet.van_speed_kmph,
                )
                if next_arrival + 1e-9 < required_arrival:
                    timing["time_window_violations"].append(
                        f"{recovery_van} position {recovery_pos + 1} arrival {next_arrival:.3f} is before propagated recovery arrival {required_arrival:.3f}."
                    )

    timing["van_arrival_by_van"] = van_arrival_by_van
    timing["van_arrival_sequence_by_van"] = van_sequence_by_van
    first_van = sorted(van_sequence_by_van, key=_van_id_sort_key)[0] if van_sequence_by_van else ""
    timing["van_arrival"] = van_arrival_by_van.get(first_van, {})
    timing["van_arrival_sequence"] = van_sequence_by_van.get(first_van, [])
    state.timing = timing
    state.metadata["timing"] = timing
    state.sync_primary_van_route()
    set_cache("timing", state, signature, timing)
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
    increment("check_solution_feasible_calls")
    signature = state.cache_signature()
    cached = get_cache("feasibility", state, signature)
    if cached is not None:
        increment("check_solution_feasible_cache_hits")
        feasible, violations = cached
        return bool(feasible), list(violations)

    violations: List[str] = []
    customers = set(data.customers)
    routes = _active_van_routes(state)
    route = state.van_route
    warehouse_num_vans = config.warehouse_num_vans(data.transshipment_nodes)
    warehouse_num_drones = config.warehouse_num_drones(data.transshipment_nodes)

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
    if not getattr(state, "tractor_routes", {}) and state.truck_route != expected_truck_route:
        violations.append(
            f"truck_route must be {expected_truck_route} for the selected transshipment."
        )

    container_load_events: Dict[int, Tuple[str, Dict[str, object]]] = {}
    container_unload_events: Dict[int, Tuple[str, Dict[str, object]]] = {}
    used_trailers = set()
    for tractor_id, tractor_route in getattr(state, "tractor_routes", {}).items():
        if not tractor_route:
            continue
        home = int(state.tractor_home.get(tractor_id, getattr(data, "tractor_depot_node", data.truck_depot_node)))
        if int(tractor_route[0].get("node", -1)) != home:
            violations.append(f"{tractor_id} route must start at tractor_home {home}.")
        if int(tractor_route[-1].get("node", -1)) != home:
            violations.append(f"{tractor_id} route must return to tractor_home {home}.")
        attached_trailer = ""
        saw_attach = False
        saw_detach = False
        active_loaded_container = None
        previous_departure = -1.0
        for event in tractor_route:
            arrival = float(event.get("arrival_time", 0.0))
            departure = float(event.get("departure_time", arrival))
            if arrival + 1e-9 < previous_departure:
                violations.append(f"{tractor_id} route times are not nondecreasing.")
            previous_departure = departure
            event_name = str(event.get("event", ""))
            trailer_id = str(event.get("trailer_id", "") or "")
            if event_name == "attach_trailer":
                if attached_trailer:
                    violations.append(f"{tractor_id} attaches {trailer_id} while already hauling {attached_trailer}.")
                attached_trailer = trailer_id
                used_trailers.add(trailer_id)
                saw_attach = True
            elif event_name == "load_container":
                if not attached_trailer:
                    violations.append(f"{tractor_id} loads container before attaching a trailer.")
                if trailer_id and trailer_id != attached_trailer:
                    violations.append(f"{tractor_id} load uses trailer {trailer_id} but attached trailer is {attached_trailer}.")
                container_id = int(event.get("container_id", -1))
                active_loaded_container = container_id
                if container_id in container_load_events:
                    violations.append(f"container {container_id} has multiple load_container events.")
                container_load_events[container_id] = (tractor_id, event)
            elif event_name == "unload_container":
                if not attached_trailer:
                    violations.append(f"{tractor_id} unloads container before attaching a trailer.")
                container_id = int(event.get("container_id", -1))
                if active_loaded_container != container_id:
                    violations.append(f"{tractor_id} unloads container {container_id} without matching loaded trailer movement.")
                if container_id in container_unload_events:
                    violations.append(f"container {container_id} has multiple unload_container events.")
                container_unload_events[container_id] = (tractor_id, event)
                active_loaded_container = None
            elif event_name == "detach_trailer":
                if not attached_trailer:
                    violations.append(f"{tractor_id} detaches trailer before attach_trailer.")
                if trailer_id and trailer_id != attached_trailer:
                    violations.append(f"{tractor_id} detaches {trailer_id} but attached trailer is {attached_trailer}.")
                attached_trailer = ""
                saw_detach = True
        if saw_attach and not saw_detach:
            violations.append(f"{tractor_id} route has attach_trailer but no detach_trailer.")
        if attached_trailer:
            violations.append(f"{tractor_id} ends while still hauling trailer {attached_trailer}.")

    for container_id, container_route in getattr(state, "container_routes", {}).items():
        container_id = int(container_id)
        origin = int(container_route.get("origin", -1))
        destination = int(container_route.get("destination_warehouse", -1))
        if destination not in state.transshipment_nodes:
            violations.append(f"container {container_id} destination_warehouse must be a candidate warehouse.")
        if "unload_complete" not in container_route:
            violations.append(f"container {container_id} has no unload_complete time.")
        load_event = container_load_events.get(container_id)
        unload_event = container_unload_events.get(container_id)
        if load_event is None or unload_event is None:
            violations.append(f"container {container_id} must have exactly one tractor/trailer movement.")
            continue
        if int(load_event[1].get("node", -1)) != origin:
            violations.append(f"container {container_id} load node does not match predefined origin {origin}.")
        if int(unload_event[1].get("node", -1)) != destination:
            violations.append(f"container {container_id} unload node does not match destination_warehouse {destination}.")
        if str(container_route.get("tractor_id", "")) != load_event[0]:
            violations.append(f"container {container_id} tractor_id does not match tractor route.")
        if str(container_route.get("trailer_id", "")) != str(load_event[1].get("trailer_id", "")):
            violations.append(f"container {container_id} trailer_id does not match load event.")
        if float(container_route.get("unload_complete", -1.0)) + 1e-9 < float(unload_event[1].get("departure_time", 0.0)):
            violations.append(f"container {container_id} unload_complete is earlier than unload event departure.")

    used_vans_by_home: Dict[int, int] = {}
    for van_id, van_route in routes.items():
        home = int(state.van_home.get(van_id, van_route[0]))
        used_vans_by_home[home] = used_vans_by_home.get(home, 0) + 1
        if len(van_route) < 2:
            violations.append(f"{van_id} route must contain at least start and end warehouse.")
            continue
        if int(van_route[0]) != home:
            violations.append(f"{van_id} must start at its home warehouse {home}.")
        if int(van_route[-1]) not in state.transshipment_nodes:
            violations.append(f"{van_id} must end at a transshipment warehouse.")
        illegal_route_nodes = [
            node
            for idx, node in enumerate(van_route)
            if node not in customers
            and not (idx in (0, len(van_route) - 1) and node in state.transshipment_nodes)
        ]
        if illegal_route_nodes:
            violations.append(f"{van_id} route contains illegal nodes: {illegal_route_nodes}")
    for warehouse, used_count in used_vans_by_home.items():
        if used_count > warehouse_num_vans.get(warehouse, 0):
            violations.append(
                f"warehouse {warehouse} uses {used_count} vans but only {warehouse_num_vans.get(warehouse, 0)} are available."
            )

    for warehouse, drone_count in warehouse_num_drones.items():
        if drone_count != warehouse_num_vans.get(warehouse, 0) * config.fleet.drones_per_van:
            violations.append(f"warehouse {warehouse} drone count is not derived from vans_per_transshipment * drones_per_van.")

    carrier_counts: Dict[str, int] = {}
    for drone_id, carrier in state.drone_initial_carrier.items():
        if carrier not in state.van_home:
            violations.append(f"{drone_id} initial carrier {carrier} is not a known van.")
            continue
        carrier_counts[carrier] = carrier_counts.get(carrier, 0) + 1
        home = int(state.van_home[carrier])
        if int(state.drone_home_warehouse.get(drone_id, home)) != home:
            violations.append(f"{drone_id} home warehouse must be derived from carrier {carrier}.")
    for van_id, count in carrier_counts.items():
        if count > config.fleet.drones_per_van:
            violations.append(f"{van_id} carries {count} drones initially, exceeding drones_per_van={config.fleet.drones_per_van}.")

    van_customers = state.get_van_customers()
    drone_customers = state.get_drone_customers()
    all_served = van_customers + drone_customers

    for customer in data.customers:
        if customer not in state.order_assignment:
            violations.append(f"customer {customer} has no order_assignment.")

    for customer, assignment in state.order_assignment.items():
        container_id = int(assignment.get("container_id", -1))
        container_route = getattr(state, "container_routes", {}).get(container_id)
        expected_destination = (
            int(container_route["destination_warehouse"])
            if isinstance(container_route, dict) and "destination_warehouse" in container_route
            else state.selected_transshipment
        )
        if int(assignment.get("assigned_transshipment", expected_destination)) != expected_destination:
            violations.append(
                f"order for customer {customer} is assigned to wrong destination warehouse."
            )
        if container_id not in getattr(state, "container_routes", {}):
            violations.append(f"order for customer {customer} references missing container {container_id}.")

    for container_id, assignment in state.container_assignment.items():
        container_route = getattr(state, "container_routes", {}).get(int(container_id), {})
        expected_destination = container_route.get("destination_warehouse")
        if assignment.get("origin_node") != state.container_origin:
            violations.append(f"container {container_id} has wrong origin node.")
        if expected_destination is not None and int(assignment.get("selected_transshipment", -1)) != int(expected_destination):
            violations.append(f"container {container_id} has wrong selected transshipment.")
        if expected_destination is not None and int(assignment.get("destination_warehouse", -1)) != int(expected_destination):
            violations.append(f"container {container_id} has wrong destination_warehouse.")
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

    van_load_trace, van_peak_payload = _van_load_trace(state, data)
    if van_peak_payload > config.fleet.van_capacity_kg + 1e-9:
        violations.append("van payload capacity exceeded.")
    for item in van_load_trace:
        if item["delivery_load_departure"] < -1e-9:
            violations.append(
                f"van delivery load becomes negative at route position {int(item['route_index'])}."
            )

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
        order = state.order_assignment.get(customer, {})
        container_id = int(order.get("container_id", -1)) if isinstance(order, dict) else -1
        container_route = getattr(state, "container_routes", {}).get(container_id)
        if isinstance(container_route, dict):
            unload_complete = float(container_route.get("unload_complete", 0.0))
            if service_start + 1e-9 < unload_complete:
                violations.append(
                    f"customer {customer} service_start {service_start:.3f} is before container {container_id} unload_complete {unload_complete:.3f}."
                )
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
    warehouse_ready_time = timing.get("warehouse_ready_time", {})
    sequences_by_van = timing.get("van_arrival_sequence_by_van", {})
    if isinstance(warehouse_ready_time, dict) and isinstance(sequences_by_van, dict):
        for van_id, sequence in sequences_by_van.items():
            if not sequence:
                continue
            first = sequence[0]
            if not isinstance(first, dict):
                continue
            warehouse = int(first.get("node", -1))
            ready_time = float(warehouse_ready_time.get(warehouse, 0.0))
            departure_time = float(first.get("departure_time", first.get("arrival_time", 0.0)))
            if departure_time + 1e-9 < ready_time:
                violations.append(
                    f"{van_id} departs warehouse {warehouse} at {departure_time:.3f} before warehouse_ready_time {ready_time:.3f}."
                )

    for sortie in state.drone_sorties:
        launch, sortie_customers, recovery = sortie_nodes(sortie)
        launch_van = _sortie_van_id(sortie, "launch_van_id", sorted(routes)[0] if routes else "van_0")
        recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
        if not sortie_customers:
            violations.append(f"drone sortie has no customers: {sortie}")
        if not config.fleet.drone_enabled:
            violations.append("drone sortie exists while drone is disabled.")
        if launch_van not in routes:
            violations.append(f"drone sortie launch_van_id is unknown: {sortie}")
        if recovery_van not in routes:
            violations.append(f"drone sortie recovery_van_id is unknown: {sortie}")
        launch_route = routes.get(launch_van, [])
        recovery_route = routes.get(recovery_van, [])
        if launch not in launch_route or recovery not in recovery_route:
            violations.append(f"drone launch/recovery not on van_route: {sortie}")
        else:
            launch_pos = _route_position(launch_route, launch)
            recovery_pos = _route_position(recovery_route, recovery)
            if launch_pos < 0 or recovery_pos < 0:
                violations.append(f"drone launch/recovery position not found on van_route: {sortie}")
            elif launch_van == recovery_van and recovery_pos < launch_pos:
                violations.append(f"drone recovery occurs before launch on van_route: {sortie}")
            elif launch_pos == len(launch_route) - 1:
                violations.append(f"drone launches after van has returned to terminal warehouse: {sortie}")
        drone_id = _sortie_drone_id(sortie)
        if drone_id not in state.drone_initial_carrier:
            violations.append(f"drone sortie uses unknown physical drone_id {drone_id}: {sortie}")
        for customer in sortie_customers:
            if customer not in customers:
                violations.append(f"drone sortie has illegal customer: {sortie}")
                continue
            if customer in van_customers:
                violations.append(f"drone customer {customer} also appears in van_route.")
            if not data.drone_eligible.get(customer, False):
                violations.append(f"customer {customer} is not drone eligible.")
        payload = drone_sortie_peak_payload(sortie, data, config)
        if payload > config.fleet.drone_capacity_kg + 1e-9:
            violations.append(f"drone payload exceeded for sortie {sortie}.")
        if drone_sortie_distance(sortie, data) > config.fleet.drone_endurance_km:
            violations.append(f"drone endurance exceeded for sortie {sortie}.")
        energy = drone_sortie_energy(sortie, data, config)
        if energy > config.fleet.drone_battery_capacity_kwh + 1e-9:
            violations.append(f"drone battery capacity exceeded for sortie {sortie}.")
        if isinstance(sortie, dict):
            if sortie.get("van_waiting_time", 0.0) < 0:
                violations.append(f"negative van waiting time in sortie: {sortie}")
            if sortie.get("drone_waiting_time", 0.0) < 0:
                violations.append(f"negative drone waiting time in sortie: {sortie}")

    used_drone_ids = {
        _sortie_drone_id(sortie)
        for sortie in state.drone_sorties
        if isinstance(sortie, dict) and _sortie_drone_id(sortie)
    }
    if len(used_drone_ids) > config.total_num_drones(data.transshipment_nodes):
        violations.append(
            f"used physical drones {len(used_drone_ids)} exceed available drones {config.total_num_drones(data.transshipment_nodes)}."
        )

    physical_sorties = timing.get("drone_physical_sorties", {})
    warehouse_launch_counts = timing.get("drone_warehouse_launch_count", {})
    warehouse_return_counts = timing.get("drone_warehouse_return_count", {})
    if isinstance(physical_sorties, dict):
        for drone_id, records in physical_sorties.items():
            if not isinstance(records, list):
                continue
            previous = None
            for record_idx, record in enumerate(records):
                if not isinstance(record, dict):
                    continue
                launch_pos = int(record.get("launch_position", -1))
                recovery_pos = int(record.get("recovery_position", -1))
                launch_node = int(record.get("launch_node", -1))
                recovery_node = int(record.get("recovery_node", -1))
                if launch_pos < 0 or recovery_pos < 0:
                    violations.append(
                        f"drone_id {drone_id} has unresolved launch/recovery position."
                    )
                if launch_pos > recovery_pos:
                    violations.append(
                        f"drone_id {drone_id} has launch_position {launch_pos} after recovery_position {recovery_pos}."
                    )
                route_for_record = routes.get(str(record.get("launch_van_id", "")), route)
                if launch_pos == len(route_for_record) - 1:
                    violations.append(
                        f"drone_id {drone_id} launches from terminal warehouse position {launch_pos}."
                    )
                if previous is not None:
                    prev_recovery_pos = int(previous.get("recovery_position", -1))
                    prev_recovery_node = int(previous.get("recovery_node", -1))
                    prev_recovery_time = float(previous.get("recovery_time", 0.0))
                    launch_time = float(record.get("launch_time", 0.0))
                    if launch_pos < prev_recovery_pos:
                        violations.append(
                            f"drone_id {drone_id} launch_position {launch_pos} is before previous recovery_position {prev_recovery_pos}."
                        )
                    if launch_time + 1e-9 < prev_recovery_time:
                        violations.append(
                            f"drone_id {drone_id} launches at {launch_time:.3f} before previous recovery_time {prev_recovery_time:.3f}."
                        )
                    if _is_warehouse_node(state, prev_recovery_node):
                        violations.append(
                            f"drone_id {drone_id} continues after recovery at warehouse node {prev_recovery_node}."
                        )
                recovery_route_for_record = routes.get(str(record.get("recovery_van_id", "")), route)
                if _is_warehouse_node(state, recovery_node) and recovery_pos == len(recovery_route_for_record) - 1:
                    later = records[record_idx + 1 :]
                    if later:
                        violations.append(
                            f"drone_id {drone_id} continues after returning to terminal warehouse."
                        )
                previous = record
            launch_count = int(warehouse_launch_counts.get(drone_id, 0))
            if launch_count > 1:
                violations.append(
                    f"drone_id {drone_id} departs from warehouse {launch_count} times."
                )
            return_count = int(warehouse_return_counts.get(drone_id, 0))
            if return_count > 1:
                violations.append(
                    f"drone_id {drone_id} returns to warehouse {return_count} times."
                )

    if float(timing.get("van_waiting_time", 0.0)) < -1e-9:
        violations.append("total van waiting time is negative.")
    if float(timing.get("drone_waiting_time", 0.0)) < -1e-9:
        violations.append("total drone waiting time is negative.")

    used_drones = len(timing.get("drone_physical_routes", {}))
    if used_drones > config.total_num_drones(data.transshipment_nodes):
        violations.append(
            f"used physical drones {used_drones} exceed owned drones {config.total_num_drones(data.transshipment_nodes)}."
        )
    for customer, high_floor in data.is_high_floor.items():
        if high_floor and state.service_mode.get(customer) != "drone":
            violations.append(f"high-floor customer {customer} must be served by drone.")

    feasible = len(violations) == 0
    set_cache("feasibility", state, signature, (feasible, list(violations)))
    return feasible, violations
