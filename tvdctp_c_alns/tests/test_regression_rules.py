from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pytest

from alns_solver import run_c_alns
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import (
    check_solution_feasible,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_peak_payload,
)
from objective import objective


@dataclass(frozen=True)
class Case:
    name: str
    num_orders: int
    num_transshipments: int
    num_containers: int
    iterations: int


CASES = [
    Case("tiny", num_orders=6, num_transshipments=2, num_containers=1, iterations=80),
    Case("small", num_orders=10, num_transshipments=2, num_containers=1, iterations=80),
    Case("medium", num_orders=20, num_transshipments=3, num_containers=2, iterations=50),
]


def _solve(case: Case):
    config = build_config(
        num_customers=case.num_orders,
        num_orders=case.num_orders,
        num_transshipments=case.num_transshipments,
        num_containers=case.num_containers,
        iterations=case.iterations,
        seed=42,
    )
    # Keep the regression fixtures focused on model-rule consistency instead
    # of resource stress; the default toy fleet has only three drones.
    config.data.high_floor_ratio = 0.15
    data = generate_toy_data(config)
    result = run_c_alns(data, config)
    total_cost, breakdown = objective(result.best_state, data, config)
    feasible, violations = check_solution_feasible(result.best_state, data, config)
    return config, data, result.best_state, total_cost, breakdown, feasible, violations


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_regression_model_rules_across_scales(case: Case) -> None:
    config, data, state, total_cost, breakdown, feasible, violations = _solve(case)

    assert feasible is True, violations
    assert state.unassigned == []

    served = state.get_van_customers() + state.get_drone_customers()
    service_counts = Counter(served)
    assert set(served) == set(data.customers)
    assert all(service_counts[customer] == 1 for customer in data.customers)

    timing = state.timing
    assert timing.get("time_window_violations", []) == []
    assert total_cost > 0

    objective_without_waiting = (
        breakdown["truck_cost"]
        + breakdown["van_cost"]
        + breakdown["drone_cost"]
        + breakdown["penalty_cost"]
    )
    assert breakdown["total_cost"] == pytest.approx(objective_without_waiting)
    assert total_cost == pytest.approx(objective_without_waiting)
    waiting_cost = breakdown.get("waiting_cost_reported", 0.0)
    if waiting_cost:
        assert total_cost != pytest.approx(objective_without_waiting + waiting_cost)

    physical_routes = timing.get("drone_physical_routes", {})
    sortie_drone_ids = {
        int(sortie["drone_id"])
        for sortie in state.drone_sorties
        if isinstance(sortie, dict) and sortie.get("drone_id") is not None
    }
    assert breakdown["used_drones"] == len(physical_routes)
    assert breakdown["used_drones"] == len(sortie_drone_ids)
    assert breakdown["used_drone_sorties"] == len(state.drone_sorties)

    for count in timing.get("drone_warehouse_launch_count", {}).values():
        assert int(count) <= 1
    for count in timing.get("drone_warehouse_return_count", {}).values():
        assert int(count) <= 1

    for sortie in state.drone_sorties:
        assert drone_sortie_energy(sortie, data, config) <= (
            config.fleet.drone_battery_capacity_kwh + 1e-9
        )
        assert drone_sortie_peak_payload(sortie, data, config) <= (
            config.fleet.drone_capacity_kg + 1e-9
        )
        assert drone_sortie_distance(sortie, data) <= (
            config.fleet.drone_endurance_km + 1e-9
        )
