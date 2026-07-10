from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

import operators
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from objective import objective


def _config(*, drone_enabled: bool = False):
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
    config.fleet.drone_enabled = drone_enabled
    return config


def _two_route_case(*, drone_enabled: bool = False):
    config = _config(drone_enabled=drone_enabled)
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    selected = int(state.selected_transshipment)
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == selected
    ]
    van_a, van_b = selected_vans[:2]
    customer, anchor_a, anchor_b = data.customers[:3]
    state.van_routes = {
        van_a: [selected, anchor_a, selected],
        van_b: [selected, anchor_b, selected],
    }
    state.sync_primary_van_route()
    state.drone_sorties = []
    state.service_mode = {item: "van" for item in data.customers}
    state.service_mode[customer] = "unassigned"
    state.unassigned = [customer]
    state.metadata["previous_van_assignment"] = {customer: van_a}
    return config, data, state, customer, van_a, van_b, anchor_a, anchor_b


def _make_all_van_candidates_feasible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(operators, "_can_van_insert", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        operators,
        "_van_insert_hard_feasible",
        lambda *args, **kwargs: True,
    )


def _real_removed_customer_case():
    config = _config(drone_enabled=True)
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    van_id = sorted(state.van_routes)[0]
    customer = int(state.van_routes[van_id][1])
    operators._remove_customer(state, customer)
    return config, data, state, customer


def _move_signature(move):
    if move is None:
        return None
    sortie = move.sortie or {}
    return (
        move.mode,
        pytest.approx(move.cost),
        move.van_id,
        sortie.get("launch_van_id"),
        sortie.get("recovery_van_id"),
        sortie.get("launch"),
        tuple(sortie.get("customers", [])),
        sortie.get("recovery"),
    )


def test_local_visits_exactly_one_target_van_route(monkeypatch: pytest.MonkeyPatch) -> None:
    config, data, state, customer, van_a, van_b, _, _ = _two_route_case()
    _make_all_van_candidates_feasible(monkeypatch)
    traces = []

    repaired = operators.greedy_van_repair(
        state,
        np.random.default_rng(7),
        data,
        config,
        trace_collector=traces.append,
    )

    assert traces[0]["target_van_id"] == van_a
    assert traces[0]["visited_van_ids"] == [van_a]
    assert van_b not in traces[0]["visited_van_ids"]
    assert customer in repaired.van_routes[van_a]


def test_global_van_generator_still_visits_all_legal_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state, customer, van_a, van_b, _, _ = _two_route_case()
    visited = []
    monkeypatch.setattr(operators, "_can_van_insert", lambda *args, **kwargs: True)

    def feasible(_customer, van_id, *_args, **_kwargs):
        visited.append(van_id)
        return True

    monkeypatch.setattr(operators, "_van_insert_hard_feasible", feasible)
    operators._best_van_move(customer, state, data, config)

    assert set(visited) == {van_a, van_b}


def test_local_and_global_candidate_sets_differ_and_global_can_choose_route_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state, customer, van_a, van_b, anchor_a, _ = _two_route_case()
    _make_all_van_candidates_feasible(monkeypatch)
    monkeypatch.setattr(
        operators,
        "_van_insert_cost",
        lambda _customer, route, _idx, _data: 100.0 if anchor_a in route else 1.0,
    )
    traces = []

    global_move = operators._best_van_move(customer, state, data, config)
    local_state = operators.greedy_van_repair(
        state,
        np.random.default_rng(7),
        data,
        config,
        trace_collector=traces.append,
    )

    assert global_move is not None and global_move.van_id == van_b
    assert traces[0]["selected_van_id"] == van_a
    assert customer in local_state.van_routes[van_a]
    assert customer not in local_state.van_routes[van_b]


def test_local_has_no_global_route_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    config, data, state, customer, van_a, van_b, _, _ = _two_route_case()
    monkeypatch.setattr(operators, "_can_van_insert", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        operators,
        "_van_insert_hard_feasible",
        lambda _customer, van_id, *_args, **_kwargs: van_id == van_b,
    )
    traces = []

    global_move = operators._best_van_move(customer, state, data, config)
    local_state = operators.greedy_van_repair(
        state,
        np.random.default_rng(7),
        data,
        config,
        trace_collector=traces.append,
    )

    assert global_move is not None and global_move.van_id == van_b
    assert local_state.unassigned == [customer]
    assert traces[0]["selected_mode"] is None
    assert traces[0]["visited_van_ids"] == [van_a]


def test_local_drone_launch_is_restricted_to_target_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state, customer, van_a, van_b, _, _ = _two_route_case(
        drone_enabled=True
    )
    data.drone_eligible = {item: True for item in data.customers}
    config.fleet.drone_capacity_kg = 1_000_000.0
    config.fleet.drone_endurance_km = 1_000_000.0
    config.fleet.drone_battery_capacity_kwh = 1_000_000.0
    monkeypatch.setattr(operators, "_best_van_move_on_route", lambda *args: None)
    monkeypatch.setattr(
        operators,
        "_drone_insert_hard_feasible",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(operators, "record_local_drone_candidate", lambda _key: True)
    traces = []

    repaired = operators.greedy_van_repair(
        state,
        np.random.default_rng(7),
        data,
        config,
        trace_collector=traces.append,
    )

    assert traces[0]["launch_van_ids"] == [van_a]
    assert van_b not in traces[0]["launch_van_ids"]
    assert traces[0]["selected_launch_van_id"] == van_a
    assert repaired.drone_sorties[0]["launch_van_id"] == van_a


def test_local_scope_preserves_cross_van_recovery() -> None:
    config = _config(drone_enabled=True)
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
    recovery_node, drone_customer = data.customers[:2]
    remaining = [
        customer
        for customer in data.customers
        if customer not in {recovery_node, drone_customer}
    ]
    state.van_routes = {
        launch_van: [selected, *remaining, selected],
        recovery_van: [selected, recovery_node, selected],
    }
    state.sync_primary_van_route()
    state.drone_sorties = []
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[drone_customer] = "unassigned"
    state.unassigned = [drone_customer]
    data.drone_distance_matrix[selected, drone_customer] = 1.0
    data.drone_distance_matrix[drone_customer, recovery_node] = 1.0
    data.drone_distance_matrix[drone_customer, selected] = 100.0
    data.drone_distance_matrix[recovery_node, drone_customer] = 100.0
    trace = {}

    move = operators._best_drone_move(
        drone_customer,
        state,
        data,
        config,
        allowed_launch_van_ids={launch_van},
        candidate_trace=trace,
    )

    assert move is not None and move.sortie is not None
    assert move.sortie["launch_van_id"] == launch_van
    assert move.sortie["recovery_van_id"] == recovery_van
    operators._apply_move(state, drone_customer, move)
    feasible, violations = check_solution_feasible(state, data, config)
    assert feasible, violations


def test_local_fixed_seed_is_deterministic_across_three_runs() -> None:
    config, data, state, _ = _real_removed_customer_case()
    runs = []

    for _ in range(3):
        traces = []
        repaired = operators.greedy_van_repair(
            state,
            np.random.default_rng(2026),
            data,
            config,
            trace_collector=traces.append,
        )
        runs.append(
            (
                traces,
                repaired.cache_signature(),
                objective(repaired, data, config)[0],
            )
        )

    assert runs[0] == runs[1] == runs[2]


def test_successful_local_repair_is_fully_feasible_and_serves_once() -> None:
    config, data, state, _ = _real_removed_customer_case()
    repaired = operators.greedy_van_repair(
        state,
        np.random.default_rng(2026),
        data,
        config,
    )

    feasible, violations = check_solution_feasible(repaired, data, config)
    served = repaired.get_van_customers() + repaired.get_drone_customers()
    counts = Counter(served)
    assert feasible, violations
    assert repaired.unassigned == []
    assert set(served) == set(data.customers)
    assert all(counts[customer] == 1 for customer in data.customers)
    assert repaired.timing.get("time_window_violations", []) == []


def test_local_candidate_count_is_strictly_less_than_global(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state, customer, _, _, _, _ = _two_route_case(drone_enabled=True)
    data.drone_eligible = {item: True for item in data.customers}
    config.fleet.drone_capacity_kg = 1_000_000.0
    config.fleet.drone_endurance_km = 1_000_000.0
    config.fleet.drone_battery_capacity_kwh = 1_000_000.0
    _make_all_van_candidates_feasible(monkeypatch)
    monkeypatch.setattr(
        operators,
        "_drone_insert_hard_feasible",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(operators, "record_local_drone_candidate", lambda _key: True)
    local_traces = []

    operators.greedy_van_repair(
        state,
        np.random.default_rng(7),
        data,
        config,
        trace_collector=local_traces.append,
    )
    global_van_calls = []

    def count_global_van(_customer, van_id, *_args, **_kwargs):
        global_van_calls.append(van_id)
        return True

    monkeypatch.setattr(operators, "_van_insert_hard_feasible", count_global_van)
    operators._best_van_move(customer, state, data, config)
    global_drone_trace = {}
    operators._best_drone_move(
        customer,
        state,
        data,
        config,
        candidate_trace=global_drone_trace,
    )

    local_count = int(local_traces[0]["van_candidate_count"]) + int(
        local_traces[0]["drone_candidate_count"]
    )
    global_count = len(global_van_calls) + int(
        global_drone_trace["drone_candidate_count"]
    )
    assert local_count < global_count


def test_global_drone_default_scope_matches_explicit_all_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state, customer, van_a, van_b, _, _ = _two_route_case(
        drone_enabled=True
    )
    data.drone_eligible = {item: True for item in data.customers}
    config.fleet.drone_capacity_kg = 1_000_000.0
    config.fleet.drone_endurance_km = 1_000_000.0
    config.fleet.drone_battery_capacity_kwh = 1_000_000.0
    monkeypatch.setattr(
        operators,
        "_drone_insert_hard_feasible",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(operators, "record_local_drone_candidate", lambda _key: True)

    default_move = operators._best_drone_move(customer, state, data, config)
    explicit_all_move = operators._best_drone_move(
        customer,
        state,
        data,
        config,
        allowed_launch_van_ids={van_a, van_b},
    )

    assert _move_signature(default_move) == _move_signature(explicit_all_move)
