from __future__ import annotations

from typing import Dict, Tuple

from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import (
    check_solution_feasible,
    compute_waiting_minutes,
    drone_sortie_distance,
    drone_sortie_energy,
)
from state import TVDState


def _route_distance(route: list[int], matrix) -> float:
    return sum(
        float(matrix[route[idx], route[idx + 1]])
        for idx in range(len(route) - 1)
    )


def _vehicle_usage_counts(state: TVDState) -> Dict[str, int]:
    used_trucks = 1 if len(state.truck_route) > 1 else 0
    used_vans = 1 if state.get_van_customers() or state.drone_sorties else 0
    physical_routes = state.timing.get("drone_physical_routes", {})
    used_drone_ids = {
        int(sortie["drone_id"])
        for sortie in state.drone_sorties
        if isinstance(sortie, dict) and sortie.get("drone_id") is not None
    }
    used_drones = (
        len(physical_routes)
        if isinstance(physical_routes, dict) and physical_routes
        else len(used_drone_ids)
    )
    return {
        "used_trucks": used_trucks,
        "used_vans": used_vans,
        "used_drones": used_drones,
        "used_drone_sorties": len(state.drone_sorties),
    }


def objective(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> Tuple[float, Dict[str, object]]:
    """Objective with vehicle transport/fixed costs, reported waiting, and penalties."""

    waiting_minutes = compute_waiting_minutes(state, data, config)
    usage = _vehicle_usage_counts(state)

    truck_distance = _route_distance(state.truck_route, data.ground_distance_matrix)
    truck_transport_cost = truck_distance * config.cost.tractor_cost_per_km
    truck_fixed_cost = usage["used_trucks"] * config.cost.tractor_fixed_cost
    truck_cost = truck_transport_cost + truck_fixed_cost

    van_distance = _route_distance(state.van_route, data.ground_distance_matrix)
    van_transport_cost = van_distance * config.cost.van_cost_per_km
    van_fixed_cost = usage["used_vans"] * config.cost.van_fixed_cost
    van_cost = van_transport_cost + van_fixed_cost

    drone_distance = sum(
        drone_sortie_distance(sortie, data)
        for sortie in state.drone_sorties
    )
    drone_energy = sum(
        drone_sortie_energy(sortie, data, config)
        for sortie in state.drone_sorties
    )
    drone_transport_cost = sum(
        drone_sortie_distance(sortie, data) * config.cost.drone_cost_per_km
        for sortie in state.drone_sorties
    )
    drone_fixed_cost = usage["used_drones"] * config.cost.drone_fixed_cost
    drone_cost = drone_transport_cost + drone_fixed_cost

    waiting_cost = waiting_minutes / 60.0 * config.cost.time_penalty_per_hour
    timing = state.timing

    feasible, violations = check_solution_feasible(state, data, config)
    penalty_cost = 0.0 if feasible else config.cost.infeasible_penalty * len(violations)

    total = (
        truck_cost
        + van_cost
        + drone_cost
        + penalty_cost
    )
    breakdown = {
        "truck_cost": float(truck_cost),
        "truck_transport_cost": float(truck_transport_cost),
        "truck_fixed_cost": float(truck_fixed_cost),
        "van_cost": float(van_cost),
        "van_transport_cost": float(van_transport_cost),
        "van_fixed_cost": float(van_fixed_cost),
        "drone_cost": float(drone_cost),
        "drone_transport_cost": float(drone_transport_cost),
        "drone_fixed_cost": float(drone_fixed_cost),
        "truck_distance": float(truck_distance),
        "van_distance": float(van_distance),
        "drone_distance": float(drone_distance),
        "drone_energy": float(drone_energy),
        **usage,
        "waiting_cost": float(waiting_cost),
        "waiting_cost_reported": float(waiting_cost),
        "penalty_cost": float(penalty_cost),
        "total_cost": float(total),
        "van_waiting_time": float(timing.get("van_waiting_time", 0.0)),
        "drone_waiting_time": float(timing.get("drone_waiting_time", 0.0)),
        "early_waiting_time": float(timing.get("early_waiting_time", 0.0)),
        "num_time_window_violations": float(
            len(timing.get("time_window_violations", []))
        ),
        "waiting_cost_reported_not_optimized": True,
        "feasible": feasible,
    }
    state.metadata["total_cost"] = float(total)
    state.metadata["cost_breakdown"] = breakdown
    state.metadata["feasibility_violations"] = violations
    state.metadata["feasible"] = feasible
    return float(total), breakdown
