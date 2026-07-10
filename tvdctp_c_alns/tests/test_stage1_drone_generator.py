from __future__ import annotations

from typing import Optional
import pytest

import operators
from config import build_config
from dataset_loader import generate_toy_data
from initial_solution import initial_solution
from operators import InsertionMove


def _drone_move_fixture():
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
    config.alns._inside_alns_loop = False
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)

    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    launch_van, recovery_van = selected_vans[:2]
    customer = data.customers[0]
    remaining = [item for item in data.customers if item != customer]
    state.van_routes = {
        launch_van: [selected, *remaining, selected],
        recovery_van: [selected, selected],
    }
    state.sync_primary_van_route()
    state.drone_sorties = []
    state.service_mode = {item: "van" for item in data.customers}
    state.service_mode[customer] = "unassigned"
    state.unassigned = [customer]
    return config, data, state, customer


def _baseline_best_drone_move(
    customer: int,
    state,
    data,
    config,
) -> Optional[InsertionMove]:
    best: Optional[InsertionMove] = None
    single = operators._best_drone_move_for_customers(
        [int(customer)], state, data, config
    )
    if single is not None:
        best = single

    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for launch_route in routes.values():
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            for recovery_route in routes.values():
                for recovery in recovery_route:
                    sortie_customers = operators._extend_drone_customers(
                        customer, launch, recovery, state, data, config
                    )
                    move = operators._best_drone_move_for_customers(
                        sortie_customers, state, data, config
                    )
                    if move is not None and (best is None or move.cost < best.cost):
                        best = move
    return best


def _move_signature(move: Optional[InsertionMove]):
    if move is None:
        return None
    sortie = move.sortie or {}
    return (
        move.mode,
        move.cost,
        tuple(int(item) for item in sortie.get("customers", [])),
        int(sortie.get("launch", -1)),
        int(sortie.get("recovery", -1)),
        str(sortie.get("drone_id", "")),
        str(sortie.get("launch_van_id", "")),
        str(sortie.get("recovery_van_id", "")),
        int(sortie.get("launch_position", -1)),
        int(sortie.get("recovery_position", -1)),
    )


def test_stage1_memo_preserves_unique_drone_candidate_keys() -> None:
    config, data, state, customer = _drone_move_fixture()
    original_generator = operators._best_drone_move_for_customers
    original_recorder = operators.record_local_drone_candidate
    calls = {"baseline": 0, "optimized": 0}
    baseline_keys = []
    optimized_keys = []
    active_keys = baseline_keys
    active_counter = "baseline"

    def counting_generator(*args, **kwargs):
        calls[active_counter] += 1
        return original_generator(*args, **kwargs)

    def collect_candidate_key(key):
        active_keys.append(key)
        return True

    operators._best_drone_move_for_customers = counting_generator
    operators.record_local_drone_candidate = collect_candidate_key
    try:
        baseline_move = _baseline_best_drone_move(customer, state, data, config)

        active_keys = optimized_keys
        active_counter = "optimized"
        optimized_move = operators._best_drone_move(customer, state, data, config)
    finally:
        operators._best_drone_move_for_customers = original_generator
        operators.record_local_drone_candidate = original_recorder

    assert set(baseline_keys) == set(optimized_keys)
    optimized_signature = _move_signature(optimized_move)
    baseline_signature = _move_signature(baseline_move)
    assert optimized_signature[0] == baseline_signature[0]
    assert optimized_signature[2:] == baseline_signature[2:]
    assert optimized_signature[1] == pytest.approx(baseline_signature[1])
    assert calls["optimized"] < calls["baseline"]
    assert len(optimized_keys) == len(set(optimized_keys))
