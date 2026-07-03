from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np

from alns_profile import (
    enter_repair,
    exit_repair,
    increment,
    record_destroy_result,
    record_repair_candidate,
    record_repair_rejection,
)
from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import (
    check_solution_feasible,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_peak_payload,
    sortie_nodes,
)
from objective import objective
from state import TVDState, default_timing


DestroyOperator = Callable[[TVDState, np.random.Generator, InstanceData, TVDConfig], TVDState]
RepairOperator = Callable[[TVDState, np.random.Generator, InstanceData, TVDConfig], TVDState]


@dataclass
class InsertionMove:
    mode: str
    cost: float
    index: Optional[int] = None
    van_id: Optional[str] = None
    sortie: Optional[dict] = None


def _removal_count(data: InstanceData, config: TVDConfig) -> int:
    return max(1, int(round(len(data.customers) * config.alns.customer_removal_ratio)))


def _served_customers(state: TVDState) -> List[int]:
    return sorted(set(state.get_van_customers() + state.get_drone_customers()))


def _record_destroy_diagnostics(
    state: TVDState,
    customers: Iterable[int],
    data: InstanceData,
    *,
    cascade_expansion_count: int = 0,
) -> None:
    selected = sorted({int(customer) for customer in customers})
    drone_customers = set(state.get_drone_customers())
    van_customers = set(state.get_van_customers())
    record_destroy_result(
        removed_customers=selected,
        high_floor_customers=[
            customer for customer in selected if data.is_high_floor.get(customer, False)
        ],
        drone_customers=[customer for customer in selected if customer in drone_customers],
        van_customers=[customer for customer in selected if customer in van_customers],
        cascade_expansion_count=cascade_expansion_count,
    )


def _remove_customer(state: TVDState, customer: int) -> None:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for van_id, route in list(routes.items()):
        if customer in route:
            routes[van_id] = [node for node in route if node != customer]
    state.van_routes = routes
    state.sync_primary_van_route()

    remaining_sorties = []
    removed_drone_customers = set()
    for sortie in state.drone_sorties:
        launch, sortie_customers, recovery = sortie_nodes(sortie)
        if customer in sortie_customers or customer in (launch, recovery):
            removed_drone_customers.update(sortie_customers)
        else:
            remaining_sorties.append(sortie)
    state.drone_sorties = remaining_sorties

    for removed_customer in sorted(removed_drone_customers | {customer}):
        state.mark_unassigned(removed_customer)


def _remove_customers(state: TVDState, customers: Iterable[int]) -> TVDState:
    for customer in customers:
        _remove_customer(state, int(customer))
    return state


def _remove_duplicate_unassigned(state: TVDState) -> None:
    seen = set()
    cleaned = []
    for customer in state.unassigned:
        if customer not in seen:
            cleaned.append(customer)
            seen.add(customer)
    state.unassigned = cleaned


def random_customer_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    served = _served_customers(destroyed)
    count = min(_removal_count(data, config), len(served))
    selected = rng.choice(served, size=count, replace=False).tolist() if served else []
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def greedy_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    """论文 greedy removal：删除边际贡献最大的客户。"""

    destroyed = state.copy()
    base_cost, _ = objective(destroyed.copy(), data, config)
    scores: List[Tuple[float, int]] = []
    for customer in _served_customers(destroyed):
        trial = destroyed.copy()
        _remove_customer(trial, customer)
        trial.clean_unassigned(customer)
        trial_cost, _ = objective(trial, data, config)
        scores.append((base_cost - trial_cost, customer))

    count = min(_removal_count(data, config), len(scores))
    selected = [customer for _, customer in sorted(scores, reverse=True)[:count]]
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def related_customer_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    served = _served_customers(destroyed)
    if not served:
        return destroyed

    seed = int(rng.choice(served))
    count = min(_removal_count(data, config), len(served))
    selected = sorted(
        served, key=lambda customer: data.ground_distance_matrix[seed, customer]
    )[:count]
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def route_segment_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    internal = destroyed.get_van_customers()
    if not internal:
        return random_customer_removal(destroyed, rng, data, config)

    count = min(_removal_count(data, config), len(internal))
    start = int(rng.integers(0, len(internal) - count + 1))
    selected = internal[start : start + count]
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def drone_task_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    if not destroyed.drone_sorties:
        return random_customer_removal(destroyed, rng, data, config)

    count = min(_removal_count(data, config), len(destroyed.drone_sorties))
    selected_idx = rng.choice(range(len(destroyed.drone_sorties)), size=count, replace=False)
    selected = []
    for idx in selected_idx:
        _, sortie_customers, _ = sortie_nodes(destroyed.drone_sorties[int(idx)])
        selected.extend(sortie_customers)
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def _cascade_dependencies(state: TVDState, customer: int) -> set[int]:
    deps = {customer}
    for sortie in state.drone_sorties:
        launch, drone_customers, recovery = sortie_nodes(sortie)
        if customer in [launch, recovery] + drone_customers:
            deps.update(drone_customers)
            if launch not in state.metadata.get("route_endpoints", []):
                deps.add(launch)
            if recovery not in state.metadata.get("route_endpoints", []):
                deps.add(recovery)
    return deps


def cascade_aware_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    served = _served_customers(destroyed)
    count = min(_removal_count(data, config), len(served))
    initial = rng.choice(served, size=count, replace=False).tolist() if served else []
    removal = set(initial)

    changed = True
    while changed:
        changed = False
        for customer in list(removal):
            deps = _cascade_dependencies(destroyed, customer)
            if not deps.issubset(removal):
                removal |= deps
                changed = True

    bundles = []
    assigned = set()
    for sortie in destroyed.drone_sorties:
        launch, drone_customers, recovery = sortie_nodes(sortie)
        related = set(drone_customers)
        if launch in data.customers:
            related.add(launch)
        if recovery in data.customers:
            related.add(recovery)
        bundle = sorted(related & removal)
        if bundle:
            bundles.append(bundle)
            assigned.update(bundle)
    for customer in sorted(removal - assigned):
        bundles.append([customer])

    _record_destroy_diagnostics(
        destroyed,
        removal,
        data,
        cascade_expansion_count=max(0, len(removal) - len(initial)),
    )
    destroyed = _remove_customers(destroyed, removal)
    _remove_duplicate_unassigned(destroyed)
    destroyed.metadata["cascade_removed"] = sorted(removal)
    destroyed.metadata["cascade_bundles"] = bundles
    return destroyed


def _truck_route_for_transshipment(data: InstanceData, selected_transshipment: int) -> List[int]:
    if data.container_origin == selected_transshipment:
        return [data.truck_depot_node, selected_transshipment]
    return [data.truck_depot_node, data.container_origin, selected_transshipment]


def _rebuild_assignments_for_transshipment(
    state: TVDState, data: InstanceData, selected_transshipment: int
) -> None:
    for assignment in state.order_assignment.values():
        container_id = int(assignment.get("container_id", -1))
        container_route = state.container_routes.get(container_id, {})
        assignment["assigned_transshipment"] = int(
            container_route.get("destination_warehouse", selected_transshipment)
        )

    for container_id, assignment in state.container_assignment.items():
        container_route = state.container_routes.get(int(container_id), {})
        destination = int(container_route.get("destination_warehouse", selected_transshipment))
        assignment["origin_node"] = data.container_origin
        assignment["candidate_transshipments"] = data.transshipment_nodes.copy()
        assignment["selected_transshipment"] = destination
        assignment["destination_warehouse"] = destination


def switch_transshipment_operator(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    """Move the solution to another candidate warehouse, then let repair rebuild service."""

    switched = state.copy()
    alternatives = [
        node
        for node in data.transshipment_nodes
        if node != switched.selected_transshipment
    ]
    if not alternatives:
        return switched

    new_transshipment = int(rng.choice(alternatives))
    old_transshipment = switched.selected_transshipment
    from initial_solution import _build_stage1_drayage

    destinations = {
        int(container_id): new_transshipment
        for container_id in data.container_assignment
    }
    (
        tractor_routes,
        container_routes,
        tractor_home,
        trailer_home,
        truck_route,
        warehouse_ready_time,
    ) = _build_stage1_drayage(data, config, destinations)
    switched.selected_transshipment = new_transshipment
    switched.truck_route = truck_route
    switched.tractor_routes = tractor_routes
    switched.tractor_home = tractor_home
    switched.trailer_home = trailer_home
    switched.container_routes = container_routes
    van_home = config.build_van_home(data.transshipment_nodes)
    drone_initial_carrier = config.build_drone_initial_carrier(data.transshipment_nodes)
    drone_home_warehouse = config.build_drone_home_warehouse(data.transshipment_nodes)
    switched.van_home = van_home
    switched.drone_initial_carrier = drone_initial_carrier
    switched.drone_home_warehouse = drone_home_warehouse
    switched.van_routes = {
        van_id: [new_transshipment, new_transshipment]
        for van_id, home in van_home.items()
        if int(home) == int(new_transshipment)
    }
    switched.sync_primary_van_route()
    switched.drone_sorties = []
    _record_destroy_diagnostics(state, data.customers, data)
    switched.unassigned = data.customers.copy()
    switched.service_mode = {customer: "unassigned" for customer in data.customers}
    switched.metadata["route_endpoints"] = sorted(set(data.transshipment_nodes))
    switched.metadata["warehouse_num_vans"] = config.warehouse_num_vans(data.transshipment_nodes)
    switched.metadata["warehouse_num_drones"] = config.warehouse_num_drones(data.transshipment_nodes)
    switched.metadata["drones_per_van"] = config.fleet.drones_per_van
    switched.metadata["warehouse_ready_time"] = warehouse_ready_time
    switched.metadata["transshipment_switched_from"] = old_transshipment
    switched.metadata["transshipment_switched_to"] = new_transshipment
    switched.timing = default_timing()
    _rebuild_assignments_for_transshipment(switched, data, new_transshipment)
    return switched


def _van_insert_cost(customer: int, route: List[int], idx: int, data: InstanceData) -> float:
    pred = route[idx - 1]
    succ = route[idx]
    dist = data.ground_distance_matrix
    return float(dist[pred, customer] + dist[customer, succ] - dist[pred, succ])


def _can_van_insert(
    customer: int,
    route: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    route_customers = [node for node in route if node in data.customers]
    current_delivery = sum(data.demands[c] for c in route_customers)
    current_pickup = sum(getattr(data, "pickup_demands", {}).get(c, 0.0) for c in route_customers)
    customer_pickup = getattr(data, "pickup_demands", {}).get(customer, 0.0)
    return current_delivery + current_pickup + data.demands[customer] + customer_pickup <= config.fleet.van_capacity_kg


def _travel_minutes(distance: float, speed_kmph: float) -> float:
    return float(distance) / speed_kmph * 60.0


def _route_payload(route: List[int], data: InstanceData) -> float:
    return float(
        sum(float(data.demands.get(node, 0.0)) for node in route if node in data.customers)
        + sum(
            float(getattr(data, "pickup_demands", {}).get(node, 0.0))
            for node in route
            if node in data.customers
        )
    )


def _warehouse_ready_times(state: TVDState) -> Dict[int, float]:
    ready = {
        int(warehouse): float(ready_time)
        for warehouse, ready_time in state.metadata.get("warehouse_ready_time", {}).items()
    }
    for container in getattr(state, "container_routes", {}).values():
        if not isinstance(container, dict):
            continue
        warehouse = int(container.get("destination_warehouse", state.selected_transshipment))
        ready[warehouse] = max(ready.get(warehouse, 0.0), float(container.get("unload_complete", 0.0)))
    return ready


def _van_route_timing_feasible(
    route: List[int],
    start_time: float,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    if len(route) < 2:
        return False
    current_time = float(start_time)
    previous = int(route[0])
    for idx, node in enumerate(route):
        node = int(node)
        if idx > 0:
            current_time += _travel_minutes(
                data.ground_distance_matrix[previous, node],
                config.fleet.van_speed_kmph,
            )
        if node in data.customers:
            earliest, latest = data.time_windows.get(node, (0.0, float("inf")))
            service_start = max(current_time, float(earliest))
            if service_start > float(latest) + 1e-9:
                return False
            current_time = service_start + float(data.service_times.get(node, 0.0))
        previous = node
    return True


def _route_service_time_at_position(
    route: List[int],
    position: int,
    start_time: float,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[float]:
    if not route or position < 0 or position >= len(route):
        return None
    current_time = float(start_time)
    previous = int(route[0])
    for idx, node in enumerate(route):
        node = int(node)
        if idx > 0:
            current_time += _travel_minutes(
                data.ground_distance_matrix[previous, node],
                config.fleet.van_speed_kmph,
            )
        if node in data.customers:
            earliest, latest = data.time_windows.get(node, (0.0, float("inf")))
            service_start = max(current_time, float(earliest))
            if service_start > float(latest) + 1e-9:
                return None
            current_time = service_start + float(data.service_times.get(node, 0.0))
        if idx == position:
            return float(current_time)
        previous = node
    return None


def _repair_van_routes(state: TVDState) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    repaired = {str(van_id): route.copy() for van_id, route in routes.items()}
    selected = int(state.selected_transshipment)
    for van_id, home in sorted(state.van_home.items(), key=lambda item: int(item[0].split("_")[1])):
        if int(home) == selected and van_id not in repaired:
            repaired[van_id] = [selected, selected]
    return repaired


def _is_allowed_partial_repair_violation(violation: str, state: TVDState) -> bool:
    if violation.startswith("unassigned customers remain:"):
        return True
    prefix = "high-floor customer "
    if violation.startswith(prefix) and " must be served by drone." in violation:
        try:
            customer = int(violation[len(prefix):].split()[0])
        except (IndexError, ValueError):
            return False
        return customer in state.unassigned
    return False


def _partial_repair_hard_feasible(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    feasible, violations = check_solution_feasible(state, data, config)
    return feasible or all(
        _is_allowed_partial_repair_violation(str(violation), state)
        for violation in violations
    )


def _van_insert_hard_feasible(
    customer: int,
    van_id: str,
    candidate_route: List[int],
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    if data.is_high_floor.get(int(customer), False):
        record_repair_rejection("van_high_floor")
        return False
    if _route_payload(candidate_route, data) > config.fleet.van_capacity_kg + 1e-9:
        record_repair_rejection("rejected_by_capacity")
        return False
    if not candidate_route or int(candidate_route[0]) not in state.transshipment_nodes:
        record_repair_rejection("van_bad_route_endpoint")
        return False
    if int(candidate_route[-1]) not in state.transshipment_nodes:
        record_repair_rejection("van_bad_route_endpoint")
        return False
    start_time = _warehouse_ready_times(state).get(int(candidate_route[0]), 0.0)
    feasible = _van_route_timing_feasible(candidate_route, start_time, data, config)
    if not feasible:
        record_repair_rejection("rejected_by_time_window")
    return feasible


def _drone_insert_hard_feasible(
    customers: List[int],
    sortie: dict,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    if not customers:
        record_repair_rejection("drone_empty_sortie")
        return False
    if any(not data.drone_eligible.get(int(customer), False) for customer in customers):
        record_repair_rejection("drone_ineligible")
        return False
    if drone_sortie_peak_payload(sortie, data, config) > config.fleet.drone_capacity_kg:
        record_repair_rejection("rejected_by_drone_payload")
        return False
    if drone_sortie_distance(sortie, data) > config.fleet.drone_endurance_km:
        record_repair_rejection("rejected_by_drone_endurance")
        return False
    if drone_sortie_energy(sortie, data, config) > config.fleet.drone_battery_capacity_kwh:
        record_repair_rejection("rejected_by_drone_energy")
        return False
    if not _can_make_drone_sortie(sortie, data, config):
        record_repair_rejection("drone_basic_feasibility")
        return False
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    launch_van_id = str(sortie.get("launch_van_id", ""))
    recovery_van_id = str(sortie.get("recovery_van_id", launch_van_id))
    launch_route = routes.get(launch_van_id)
    recovery_route = routes.get(recovery_van_id)
    if launch_route is None or recovery_route is None:
        record_repair_rejection("rejected_by_sync")
        return False
    launch = int(sortie.get("launch", -1))
    recovery = int(sortie.get("recovery", -1))
    launch_pos = int(sortie.get("launch_position", -1))
    recovery_pos = int(sortie.get("recovery_position", -1))
    if not (0 <= launch_pos < len(launch_route) and int(launch_route[launch_pos]) == launch):
        record_repair_rejection("rejected_by_sync")
        return False
    if not (0 <= recovery_pos < len(recovery_route) and int(recovery_route[recovery_pos]) == recovery):
        record_repair_rejection("rejected_by_sync")
        return False
    if launch_pos == len(launch_route) - 1:
        record_repair_rejection("rejected_by_sync")
        return False
    if launch_van_id == recovery_van_id:
        if recovery_pos < launch_pos:
            record_repair_rejection("rejected_by_sync")
            return False
        if launch == recovery and recovery_pos != launch_pos:
            record_repair_rejection("rejected_by_sync")
            return False

    ready = _warehouse_ready_times(state)
    launch_time = _route_service_time_at_position(
        launch_route,
        launch_pos,
        ready.get(int(launch_route[0]), 0.0),
        data,
        config,
    )
    recovery_arrival = _route_service_time_at_position(
        recovery_route,
        recovery_pos,
        ready.get(int(recovery_route[0]), 0.0),
        data,
        config,
    )
    if launch_time is None or recovery_arrival is None:
        record_repair_rejection("rejected_by_sync")
        return False

    drone_time = float(launch_time)
    previous = launch
    for sortie_customer in customers:
        sortie_customer = int(sortie_customer)
        drone_time += _travel_minutes(
            data.drone_distance_matrix[previous, sortie_customer],
            config.fleet.drone_speed_kmph,
        )
        earliest, latest = data.time_windows.get(sortie_customer, (0.0, float("inf")))
        service_start = max(drone_time, float(earliest))
        if service_start > float(latest) + 1e-9:
            record_repair_rejection("rejected_by_time_window")
            return False
        drone_time = service_start + float(data.service_times.get(sortie_customer, 0.0))
        previous = sortie_customer
    drone_time += _travel_minutes(
        data.drone_distance_matrix[previous, recovery],
        config.fleet.drone_speed_kmph,
    )
    return drone_time >= 0.0 and float(recovery_arrival) >= 0.0


def _best_van_move(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> Optional[InsertionMove]:
    if data.is_high_floor.get(int(customer), False):
        return None
    best: Optional[InsertionMove] = None
    routes = _repair_van_routes(state)
    for van_id, route in routes.items():
        if not _can_van_insert(customer, route, data, config):
            continue
        fixed_delta = 0.0 if len(route) > 2 else config.cost.van_fixed_cost
        for idx in range(1, len(route)):
            increment("van_insert_candidates")
            increment("service_mode_switch_candidates")
            if len(route) <= 2:
                increment("new_van_activation_candidates")
            candidate_route = route[:idx] + [int(customer)] + route[idx:]
            feasible = _van_insert_hard_feasible(
                customer,
                van_id,
                candidate_route,
                state,
                data,
                config,
            )
            record_repair_candidate("van", feasible)
            if not feasible:
                continue
            delta = _van_insert_cost(customer, route, idx, data)
            cost = delta * config.cost.van_cost_per_km + fixed_delta
            if best is None or cost < best.cost:
                best = InsertionMove(mode="van", cost=cost, index=idx, van_id=van_id)
    return best


def _drone_payload(customers: List[int], data: InstanceData) -> float:
    delivery = sum(data.demands[customer] for customer in customers)
    pickup = sum(getattr(data, "pickup_demands", {}).get(customer, 0.0) for customer in customers)
    return float(delivery + pickup)


def _can_make_drone_sortie(sortie: dict, data: InstanceData, config: TVDConfig) -> bool:
    _, customers, _ = sortie_nodes(sortie)
    if not customers:
        return False
    if any(not data.drone_eligible.get(customer, False) for customer in customers):
        return False
    if drone_sortie_peak_payload(sortie, data, config) > config.fleet.drone_capacity_kg:
        return False
    return (
        drone_sortie_distance(sortie, data) <= config.fleet.drone_endurance_km
        and drone_sortie_energy(sortie, data, config)
        <= config.fleet.drone_battery_capacity_kwh
    )


def _first_drone_for_van(state: TVDState, van_id: str) -> str:
    return next(
        (
            candidate_drone
            for candidate_drone, carrier in state.drone_initial_carrier.items()
            if carrier == van_id
        ),
        "",
    )


def _extend_drone_customers(
    seed_customer: int,
    launch: int,
    recovery: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[int]:
    customers = [int(seed_customer)]
    while True:
        best_candidate = None
        best_distance = None
        for candidate in state.unassigned:
            candidate = int(candidate)
            if candidate in customers:
                continue
            if not data.drone_eligible.get(candidate, False):
                continue
            if any(candidate in route for route in state.van_routes.values()):
                continue
            trial_customers = customers + [candidate]
            trial_sortie = _make_drone_sortie(launch, trial_customers, recovery)
            if not _can_make_drone_sortie(trial_sortie, data, config):
                continue
            distance = drone_sortie_distance(trial_sortie, data)
            if best_distance is None or distance < best_distance:
                best_candidate = candidate
                best_distance = distance

        if best_candidate is None:
            break
        customers.append(best_candidate)
    return customers


def _best_drone_move_for_customers(
    customers: List[int],
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[InsertionMove]:
    if not config.fleet.drone_enabled or not customers:
        return None
    if any(not data.drone_eligible.get(customer, False) for customer in customers):
        return None
    if _drone_payload(customers, data) > config.fleet.drone_capacity_kg:
        return None

    best: Optional[InsertionMove] = None
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    existing_drone_ids = {
        str(existing.get("drone_id"))
        for existing in state.drone_sorties
        if isinstance(existing, dict)
    }
    existing_van_ids = {
        van_id
        for van_id, route in routes.items()
        if len(route) > 2
        or any(
            isinstance(sortie, dict)
            and (
                sortie.get("launch_van_id") == van_id
                or sortie.get("recovery_van_id") == van_id
            )
            for sortie in state.drone_sorties
        )
    }

    for launch_van_id, launch_route in routes.items():
        drone_id = _first_drone_for_van(state, launch_van_id)
        if not drone_id:
            continue
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            if int(launch) in customers:
                continue
            for recovery_van_id, recovery_route in routes.items():
                for recovery_pos, recovery in enumerate(recovery_route):
                    if int(recovery) in customers:
                        continue
                    if launch_van_id == recovery_van_id:
                        if recovery_pos < launch_pos:
                            continue
                        if launch == recovery and recovery_pos != launch_pos:
                            continue
                    sortie = _make_drone_sortie(
                        launch,
                        customers,
                        recovery,
                        drone_id=drone_id,
                        launch_van_id=launch_van_id,
                        recovery_van_id=recovery_van_id,
                    )
                    sortie["launch_position"] = int(launch_pos)
                    sortie["recovery_position"] = int(recovery_pos)
                    increment("drone_insert_candidates")
                    increment("service_mode_switch_candidates")
                    if launch_van_id != recovery_van_id:
                        increment("cross_van_docking_candidates")
                    for van_id in {launch_van_id, recovery_van_id}:
                        if van_id not in existing_van_ids:
                            increment("new_van_activation_candidates")
                    feasible = _drone_insert_hard_feasible(
                        customers,
                        sortie,
                        state,
                        data,
                        config,
                    )
                    record_repair_candidate("drone", feasible)
                    if not feasible:
                        continue
                    fixed_delta = (
                        0.0
                        if drone_id in existing_drone_ids
                        else config.cost.drone_fixed_cost
                    )
                    van_fixed_delta = sum(
                        config.cost.van_fixed_cost
                        for van_id in {launch_van_id, recovery_van_id}
                        if van_id not in existing_van_ids
                    )
                    cost = (
                        drone_sortie_distance(sortie, data) * config.cost.drone_cost_per_km
                        + fixed_delta
                        + van_fixed_delta
                    )
                    move = InsertionMove(mode="drone", cost=cost, sortie=sortie)
                    if best is None or cost < best.cost:
                        best = move
    return best


def _sortie_van_id(sortie: dict, field: str, fallback: str = "") -> str:
    value = sortie.get(field, fallback) if isinstance(sortie, dict) else fallback
    return str(value or fallback)


def _sortie_drone_id(sortie: dict) -> str:
    value = sortie.get("drone_id", "") if isinstance(sortie, dict) else ""
    return str(value or "")


def _copy_sortie_with_route(template: dict, launch: int, customers: List[int], recovery: int) -> dict:
    launch_pos = template.get("launch_position", 0)
    recovery_pos = template.get("recovery_position", launch_pos)
    return _make_drone_sortie(
        launch,
        customers,
        recovery,
        drone_id=_sortie_drone_id(template),
        launch_van_id=_sortie_van_id(template, "launch_van_id"),
        recovery_van_id=_sortie_van_id(
            template,
            "recovery_van_id",
            _sortie_van_id(template, "launch_van_id"),
        ),
    ) | {
        "launch_position": int(launch_pos),
        "recovery_position": int(recovery_pos),
    }


def _state_is_feasible_and_no_worse(
    base: TVDState,
    candidate: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    feasible, _ = check_solution_feasible(candidate, data, config)
    if not feasible:
        return False
    base_cost, _ = objective(base.copy(), data, config)
    candidate_cost, _ = objective(candidate, data, config)
    return candidate_cost <= base_cost + 1e-9


def _replace_sorties_with_merged(
    state: TVDState,
    indices: List[int],
    merged_sortie: dict,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    candidate = state.copy()
    remove_set = set(indices)
    candidate.drone_sorties = [
        sortie for idx, sortie in enumerate(candidate.drone_sorties) if idx not in remove_set
    ]
    candidate.drone_sorties.append(merged_sortie)
    for customer in sortie_nodes(merged_sortie)[1]:
        candidate.service_mode[int(customer)] = "drone"
    if _state_is_feasible_and_no_worse(state, candidate, data, config):
        return candidate
    return None


def _merge_sortie_group(
    state: TVDState,
    group: List[Tuple[int, dict]],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    ordered = sorted(
        group,
        key=lambda item: (
            float(item[1].get("launch_time", 0.0)),
            int(item[1].get("launch_position", 0)),
            int(item[0]),
        ),
    )
    for candidate_group in [ordered] + [
        list(pair) for pair in combinations(ordered, 2)
    ]:
        customers: List[int] = []
        for _, sortie in candidate_group:
            customers.extend(sortie_nodes(sortie)[1])
        if len(set(customers)) != len(customers):
            continue
        first_sortie = candidate_group[0][1]
        launch, _, recovery = sortie_nodes(first_sortie)
        merged_sortie = _copy_sortie_with_route(first_sortie, launch, customers, recovery)
        if not _can_make_drone_sortie(merged_sortie, data, config):
            continue
        merged = _replace_sorties_with_merged(
            state,
            [idx for idx, _ in candidate_group],
            merged_sortie,
            data,
            config,
        )
        if merged is not None:
            return merged
    return None


def _merge_adjacent_same_van_pair(
    state: TVDState,
    group: List[Tuple[int, dict]],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    ordered = sorted(
        group,
        key=lambda item: (
            int(item[1].get("launch_position", 0)),
            int(item[1].get("recovery_position", 0)),
            float(item[1].get("launch_time", 0.0)),
        ),
    )
    for left, right in zip(ordered, ordered[1:]):
        left_idx, left_sortie = left
        right_idx, right_sortie = right
        launch, left_customers, _ = sortie_nodes(left_sortie)
        _, right_customers, recovery = sortie_nodes(right_sortie)
        customers = left_customers + right_customers
        if len(set(customers)) != len(customers):
            continue
        merged_sortie = _copy_sortie_with_route(left_sortie, launch, customers, recovery)
        merged_sortie["recovery_position"] = int(right_sortie.get("recovery_position", 0))
        merged_sortie["recovery"] = int(recovery)
        merged_sortie["recovery_van_id"] = _sortie_van_id(
            right_sortie,
            "recovery_van_id",
            _sortie_van_id(left_sortie, "recovery_van_id"),
        )
        if not _can_make_drone_sortie(merged_sortie, data, config):
            continue
        merged = _replace_sorties_with_merged(
            state,
            [left_idx, right_idx],
            merged_sortie,
            data,
            config,
        )
        if merged is not None:
            return merged
    return None


def consolidate_drone_sorties(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> TVDState:
    """Merge compatible drone sorties when doing so is feasible and no worse."""

    feasible, _ = check_solution_feasible(state, data, config)
    if not feasible or len(state.drone_sorties) < 2:
        return state

    consolidated = state.copy()
    progress = True
    while progress:
        progress = False
        exact_groups: Dict[Tuple[object, ...], List[Tuple[int, dict]]] = {}
        same_van_groups: Dict[Tuple[object, ...], List[Tuple[int, dict]]] = {}
        for idx, sortie in enumerate(consolidated.drone_sorties):
            if not isinstance(sortie, dict):
                continue
            launch, _, recovery = sortie_nodes(sortie)
            launch_van = _sortie_van_id(sortie, "launch_van_id")
            recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
            exact_groups.setdefault(
                (launch_van, recovery_van, int(launch), int(recovery)),
                [],
            ).append((idx, sortie))
            same_van_groups.setdefault((launch_van, recovery_van), []).append(
                (idx, sortie)
            )

        for group in exact_groups.values():
            if len(group) < 2:
                continue
            merged = _merge_sortie_group(consolidated, group, data, config)
            if merged is not None:
                consolidated = merged
                progress = True
                break
        if progress:
            continue

        for group in same_van_groups.values():
            if len(group) < 2:
                continue
            merged = _merge_adjacent_same_van_pair(consolidated, group, data, config)
            if merged is not None:
                consolidated = merged
                progress = True
                break

    return consolidated


def _best_drone_move(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> Optional[InsertionMove]:
    if not config.fleet.drone_enabled or not data.drone_eligible.get(customer, False):
        return None
    if data.demands[customer] + getattr(data, "pickup_demands", {}).get(customer, 0.0) > config.fleet.drone_capacity_kg:
        return None

    best: Optional[InsertionMove] = None
    single_customer_move = _best_drone_move_for_customers(
        [int(customer)], state, data, config
    )
    if single_customer_move is not None:
        best = single_customer_move

    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for launch_route in routes.values():
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            for recovery_route in routes.values():
                for recovery in recovery_route:
                    sortie_customers = _extend_drone_customers(
                        customer, launch, recovery, state, data, config
                    )
                    move = _best_drone_move_for_customers(
                        sortie_customers, state, data, config
                    )
                    if move is not None and (best is None or move.cost < best.cost):
                        best = move
    return best


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


def _all_moves(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> List[InsertionMove]:
    moves = []
    van = _best_van_move(customer, state, data, config)
    drone = _best_drone_move(customer, state, data, config)
    if van is not None and not data.is_high_floor.get(customer, False):
        moves.append(van)
    if drone is not None:
        moves.append(drone)
    return sorted(moves, key=lambda move: move.cost)


def _finalize_repair(state: TVDState, data: InstanceData, config: TVDConfig) -> TVDState:
    return consolidate_drone_sorties(state, data, config)


def _apply_move(state: TVDState, customer: int, move: InsertionMove) -> None:
    if move.mode == "van":
        assert move.index is not None
        assert move.van_id is not None
        state.van_routes.setdefault(
            move.van_id,
            [int(state.van_home.get(move.van_id, state.selected_transshipment)), int(state.selected_transshipment)],
        )
        state.van_routes[move.van_id].insert(move.index, customer)
        state.sync_primary_van_route()
        state.service_mode[customer] = "van"
    elif move.mode == "drone":
        assert move.sortie is not None
        state.drone_sorties.append(move.sortie)
        _, sortie_customers, _ = sortie_nodes(move.sortie)
        for drone_customer in sortie_customers:
            state.service_mode[drone_customer] = "drone"
            state.clean_unassigned(drone_customer)
    else:
        raise ValueError(f"unknown insertion mode: {move.mode}")
    state.clean_unassigned(customer)


def greedy_van_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("greedy_van_repair")
    try:
        repaired = state.copy()
        rng.shuffle(repaired.unassigned)
        for customer in repaired.unassigned.copy():
            if customer not in repaired.unassigned:
                continue
            if data.is_high_floor.get(customer, False):
                continue
            move = _best_van_move(customer, repaired, data, config)
            if move is not None:
                _apply_move(repaired, customer, move)
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("greedy_van_repair")


def greedy_drone_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("greedy_drone_repair")
    try:
        repaired = state.copy()
        for customer in repaired.unassigned.copy():
            if customer not in repaired.unassigned:
                continue
            move = _best_drone_move(customer, repaired, data, config)
            if move is not None:
                _apply_move(repaired, customer, move)
        if repaired.unassigned:
            repaired = greedy_van_repair(repaired, rng, data, config)
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("greedy_drone_repair")


def best_mode_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("best_mode_repair")
    try:
        repaired = state.copy()
        for customer in repaired.unassigned.copy():
            if customer not in repaired.unassigned:
                continue
            moves = _all_moves(customer, repaired, data, config)
            if moves:
                _apply_move(repaired, customer, moves[0])
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("best_mode_repair")


def regret_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("regret_repair")
    try:
        repaired = state.copy()
        while repaired.unassigned:
            best_choice = None
            for customer in repaired.unassigned:
                moves = _all_moves(customer, repaired, data, config)
                if not moves:
                    continue
                regret = (moves[1].cost - moves[0].cost) if len(moves) > 1 else moves[0].cost
                candidate = (regret, customer, moves[0])
                if best_choice is None or candidate[0] > best_choice[0]:
                    best_choice = candidate

            if best_choice is None:
                break
            _, customer, move = best_choice
            _apply_move(repaired, customer, move)
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("regret_repair")


def _finish_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    finished = state.copy()
    progress = True
    while finished.unassigned and progress:
        progress = False
        for customer in finished.unassigned.copy():
            moves = _all_moves(customer, finished, data, config)
            if moves:
                _apply_move(finished, customer, moves[0])
                progress = True
    return finished


def _candidate_score(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Optional[float]:
    feasible, _ = check_solution_feasible(state, data, config)
    if not feasible:
        return None
    total, _ = objective(state, data, config)
    return float(total)


def _repair_bundle_all_van(
    state: TVDState,
    bundle: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    candidate = state.copy()
    for customer in bundle:
        if customer not in candidate.unassigned:
            continue
        move = _best_van_move(customer, candidate, data, config)
        if move is None:
            return None
        _apply_move(candidate, customer, move)
    return candidate


def _repair_bundle_best_modes(
    state: TVDState,
    bundle: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    candidate = state.copy()
    for customer in bundle:
        if customer not in candidate.unassigned:
            continue
        moves = _all_moves(customer, candidate, data, config)
        if not moves:
            return None
        _apply_move(candidate, customer, moves[0])
    return candidate


def _repair_bundle_as_drone(
    state: TVDState,
    bundle: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    if any(customer not in state.unassigned for customer in bundle):
        return None
    candidate = state.copy()
    move = _best_drone_move_for_customers(bundle, candidate, data, config)
    if move is None:
        return None
    _apply_move(candidate, bundle[0], move)
    return candidate


def _repair_bundle_partial_candidates(
    state: TVDState,
    bundle: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> List[TVDState]:
    if len(bundle) < 2 or len(bundle) > 3:
        return []

    candidates: List[TVDState] = []
    bundle_set = set(bundle)
    for size in range(1, len(bundle)):
        for drone_part_tuple in combinations(bundle, size):
            drone_part = list(drone_part_tuple)
            van_part = [customer for customer in bundle if customer not in drone_part_tuple]
            candidate = state.copy()
            move = _best_drone_move_for_customers(drone_part, candidate, data, config)
            if move is None:
                continue
            _apply_move(candidate, drone_part[0], move)
            failed = False
            for customer in van_part:
                if customer not in candidate.unassigned:
                    continue
                van_move = _best_van_move(customer, candidate, data, config)
                if van_move is None:
                    failed = True
                    break
                _apply_move(candidate, customer, van_move)
            if failed:
                continue
            if bundle_set.isdisjoint(candidate.unassigned):
                candidates.append(candidate)
    return candidates


def _best_bundle_repair(
    state: TVDState,
    bundle: List[int],
    rng: np.random.Generator,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    candidates = []
    builders = (
        _repair_bundle_all_van,
        _repair_bundle_best_modes,
        _repair_bundle_as_drone,
    )
    for builder in builders:
        candidate = builder(state, bundle, data, config)
        if candidate is None:
            continue
        candidate = _finish_repair(candidate, rng, data, config)
        score = _candidate_score(candidate, data, config)
        if score is not None:
            candidates.append((score, candidate))
    for candidate in _repair_bundle_partial_candidates(state, bundle, data, config):
        candidate = _finish_repair(candidate, rng, data, config)
        score = _candidate_score(candidate, data, config)
        if score is not None:
            candidates.append((score, candidate))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def cascade_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("cascade_repair")
    try:
        repaired = state.copy()
        raw_bundles = repaired.metadata.get("cascade_bundles") or [
            repaired.unassigned.copy()
        ]
        bundles = [
            sorted(
                {int(customer) for customer in bundle if int(customer) in repaired.unassigned},
                key=lambda customer: (not data.is_high_floor.get(customer, False), customer),
            )
            for bundle in raw_bundles
            if bundle
        ]
        for bundle in bundles:
            bundle = [customer for customer in bundle if customer in repaired.unassigned]
            if not bundle:
                continue
            candidate = _best_bundle_repair(repaired, bundle, rng, data, config)
            if candidate is not None:
                repaired = candidate
            else:
                for customer in bundle:
                    if customer not in repaired.unassigned:
                        continue
                    moves = _all_moves(customer, repaired, data, config)
                    if moves:
                        _apply_move(repaired, customer, moves[0])

        ordered = sorted(
            repaired.unassigned.copy(),
            key=lambda customer: (not data.is_high_floor.get(customer, False), customer),
        )
        for customer in ordered:
            if customer not in repaired.unassigned:
                continue
            moves = _all_moves(customer, repaired, data, config)
            if moves:
                _apply_move(repaired, customer, moves[0])
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("cascade_repair")


DESTROY_OPERATORS: Dict[str, DestroyOperator] = {
    "random_customer_removal": random_customer_removal,
    "greedy_removal": greedy_removal,
    "related_customer_removal": related_customer_removal,
    "route_segment_removal": route_segment_removal,
    "drone_task_removal": drone_task_removal,
    "cascade_aware_removal": cascade_aware_removal,
    "switch_transshipment_operator": switch_transshipment_operator,
}

REPAIR_OPERATORS: Dict[str, RepairOperator] = {
    "greedy_van_repair": greedy_van_repair,
    "greedy_drone_repair": greedy_drone_repair,
    "best_mode_repair": best_mode_repair,
    "regret_repair": regret_repair,
    "cascade_repair": cascade_repair,
}


def repair_is_complete(state: TVDState, data: InstanceData, config: TVDConfig) -> bool:
    feasible, _ = check_solution_feasible(state, data, config)
    return feasible
