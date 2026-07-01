from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np

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
    initial = random_customer_removal(destroyed, rng, data, config).unassigned
    removal = set(initial)

    changed = True
    while changed:
        changed = False
        for customer in list(removal):
            deps = _cascade_dependencies(destroyed, customer)
            if not deps.issubset(removal):
                removal |= deps
                changed = True

    destroyed = _remove_customers(destroyed, removal)
    _remove_duplicate_unassigned(destroyed)
    destroyed.metadata["cascade_removed"] = sorted(removal)
    return destroyed


def _truck_route_for_transshipment(data: InstanceData, selected_transshipment: int) -> List[int]:
    if data.container_origin == selected_transshipment:
        return [data.truck_depot_node, selected_transshipment]
    return [data.truck_depot_node, data.container_origin, selected_transshipment]


def _rebuild_assignments_for_transshipment(
    state: TVDState, data: InstanceData, selected_transshipment: int
) -> None:
    for assignment in state.order_assignment.values():
        assignment["assigned_transshipment"] = selected_transshipment

    for assignment in state.container_assignment.values():
        assignment["origin_node"] = data.container_origin
        assignment["candidate_transshipments"] = data.transshipment_nodes.copy()
        assignment["selected_transshipment"] = selected_transshipment


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
    switched.selected_transshipment = new_transshipment
    switched.truck_route = _truck_route_for_transshipment(data, new_transshipment)
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
    switched.unassigned = data.customers.copy()
    switched.service_mode = {customer: "unassigned" for customer in data.customers}
    switched.metadata["route_endpoints"] = sorted(set(data.transshipment_nodes))
    switched.metadata["warehouse_num_vans"] = config.warehouse_num_vans(data.transshipment_nodes)
    switched.metadata["warehouse_num_drones"] = config.warehouse_num_drones(data.transshipment_nodes)
    switched.metadata["drones_per_van"] = config.fleet.drones_per_van
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


def _best_van_move(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> Optional[InsertionMove]:
    best: Optional[InsertionMove] = None
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for van_id, route in routes.items():
        if not _can_van_insert(customer, route, data, config):
            continue
        fixed_delta = 0.0 if len(route) > 2 else config.cost.van_fixed_cost
        for idx in range(1, len(route)):
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


def _best_drone_move(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> Optional[InsertionMove]:
    if not config.fleet.drone_enabled or not data.drone_eligible.get(customer, False):
        return None
    if data.demands[customer] + getattr(data, "pickup_demands", {}).get(customer, 0.0) > config.fleet.drone_capacity_kg:
        return None

    best_cross: Optional[InsertionMove] = None
    best_same: Optional[InsertionMove] = None
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for van_id, route in routes.items():
        route_positions = list(enumerate(route))
        drone_id = next(
            (
                candidate_drone
                for candidate_drone, carrier in state.drone_initial_carrier.items()
                if carrier == van_id
            ),
            "",
        )
        for launch_pos, launch in route_positions:
            if launch_pos == len(route) - 1:
                continue
            for recovery_pos, recovery in route_positions[launch_pos:]:
                if launch == recovery and recovery_pos != launch_pos:
                    continue
                sortie_customers = _extend_drone_customers(
                    customer, launch, recovery, state, data, config
                )
                sortie = _make_drone_sortie(
                    launch,
                    sortie_customers,
                    recovery,
                    drone_id=drone_id,
                    launch_van_id=van_id,
                    recovery_van_id=van_id,
                )
                sortie["launch_position"] = int(launch_pos)
                sortie["recovery_position"] = int(recovery_pos)
                if not _can_make_drone_sortie(sortie, data, config):
                    continue
                dist = drone_sortie_distance(sortie, data)
                fixed_delta = 0.0 if drone_id in {
                    str(existing.get("drone_id"))
                    for existing in state.drone_sorties
                    if isinstance(existing, dict)
                } else config.cost.drone_fixed_cost
                cost = dist * config.cost.drone_cost_per_km + fixed_delta
                move = InsertionMove(mode="drone", cost=cost, sortie=sortie)
                if launch != recovery:
                    if best_cross is None or cost < best_cross.cost:
                        best_cross = move
                elif best_same is None or cost < best_same.cost:
                    best_same = move
    return best_cross if best_cross is not None else best_same


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
    if van is not None and not config.fleet.drone_enabled:
        moves.append(van)
    return sorted(moves, key=lambda move: move.cost)


def _apply_move(state: TVDState, customer: int, move: InsertionMove) -> None:
    if move.mode == "van":
        assert move.index is not None
        assert move.van_id is not None
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
    repaired = state.copy()
    rng.shuffle(repaired.unassigned)
    for customer in repaired.unassigned.copy():
        if customer not in repaired.unassigned:
            continue
        move = _best_van_move(customer, repaired, data, config)
        if move is not None:
            _apply_move(repaired, customer, move)
    return repaired


def greedy_drone_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    repaired = state.copy()
    for customer in repaired.unassigned.copy():
        if customer not in repaired.unassigned:
            continue
        move = _best_drone_move(customer, repaired, data, config)
        if move is not None:
            _apply_move(repaired, customer, move)
    if repaired.unassigned:
        repaired = greedy_van_repair(repaired, rng, data, config)
    return repaired


def best_mode_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    repaired = state.copy()
    for customer in repaired.unassigned.copy():
        if customer not in repaired.unassigned:
            continue
        moves = _all_moves(customer, repaired, data, config)
        if moves:
            _apply_move(repaired, customer, moves[0])
    return repaired


def regret_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
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
    return repaired


def cascade_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    repaired = state.copy()
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
    return repaired


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
