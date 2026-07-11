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


def _config(*, drone_enabled: bool = True):
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={3: 2, 4: 2},
        drones_per_van=2,
        drone_enabled=drone_enabled,
    )
    config.data.high_floor_ratio = 0.0
    return config


def _base_case(*, drone_enabled: bool = True):
    config = _config(drone_enabled=drone_enabled)
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    return config, data, state


def _cross_van_case():
    config, data, state = _base_case()
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
    return config, data, state, drone_customer, launch_van, recovery_van


def _van(cost: float, tag: int = 0):
    return operators.InsertionMove(
        mode="van",
        cost=float(cost),
        index=tag + 1,
        van_id=f"van_{tag}",
    )


def _drone(cost: float, tag: int = 0):
    return operators.InsertionMove(
        mode="drone",
        cost=float(cost),
        sortie={
            "launch": 3,
            "customers": [5],
            "recovery": 3 + tag,
            "drone_id": f"drone_{tag}",
            "launch_van_id": "van_0",
            "recovery_van_id": f"van_{tag}",
            "launch_position": 0,
            "recovery_position": tag,
        },
    )


def _stats(moves):
    return {
        "raw_candidate_count": len(moves),
        "unique_candidate_count": len(moves),
        "van_candidate_count": sum(move.mode == "van" for move in moves),
        "drone_candidate_count": sum(move.mode == "drone" for move in moves),
        "enumeration_seconds": 0.0,
    }


def _evaluate_synthetic(monkeypatch: pytest.MonkeyPatch, moves):
    config, data, state = _base_case()
    customer = data.customers[0]
    monkeypatch.setattr(
        operators,
        "_enumerate_regret_moves",
        lambda *_args, **_kwargs: (list(moves), _stats(moves)),
    )
    evaluation, _ = operators._evaluate_regret_customer(
        customer, state, data, config, original_order=0
    )
    assert evaluation is not None
    return evaluation


def test_regret2_top_two_can_both_be_van(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluation = _evaluate_synthetic(
        monkeypatch, [_van(10, 0), _van(12, 1), _drone(20, 0)]
    )
    assert evaluation.best_move.mode == "van"
    assert evaluation.second_move is not None
    assert evaluation.second_move.mode == "van"
    assert evaluation.regret == pytest.approx(2.0)


def test_regret2_top_two_can_both_be_drone(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluation = _evaluate_synthetic(
        monkeypatch, [_drone(8, 0), _drone(9, 1), _van(15, 0)]
    )
    assert evaluation.best_move.mode == "drone"
    assert evaluation.second_move is not None
    assert evaluation.second_move.mode == "drone"
    assert evaluation.regret == pytest.approx(1.0)


def test_regret2_top_two_can_be_van_then_drone(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluation = _evaluate_synthetic(
        monkeypatch, [_van(7, 0), _drone(11, 0), _van(13, 1)]
    )
    assert (evaluation.best_move.mode, evaluation.second_move.mode) == (
        "van",
        "drone",
    )
    assert evaluation.regret == pytest.approx(4.0)


def test_regret2_top_two_can_be_drone_then_van(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluation = _evaluate_synthetic(
        monkeypatch, [_drone(6, 0), _van(10, 0), _drone(12, 1)]
    )
    assert (evaluation.best_move.mode, evaluation.second_move.mode) == (
        "drone",
        "van",
    )
    assert evaluation.regret == pytest.approx(4.0)


def test_all_feasible_positions_on_same_van_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer = data.customers[0]
    route = state.van_routes["van_0"]
    operators._remove_customer(state, customer)
    monkeypatch.setattr(operators, "_can_van_insert", lambda *args: True)
    monkeypatch.setattr(
        operators, "_van_insert_hard_feasible", lambda *args, **kwargs: True
    )

    moves = operators._enumerate_feasible_van_moves(customer, state, data, config)
    van_0_positions = {
        move.index for move in moves if move.van_id == "van_0"
    }

    assert len(route) - 1 >= 2
    assert len(van_0_positions) >= 2


def test_all_drone_launch_recovery_combinations_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case()
    customer = data.customers[0]
    operators._remove_customer(state, customer)
    data.drone_eligible = {item: True for item in data.customers}
    config.fleet.drone_capacity_kg = 1_000_000.0
    config.fleet.drone_endurance_km = 1_000_000.0
    config.fleet.drone_battery_capacity_kwh = 1_000_000.0
    monkeypatch.setattr(
        operators, "_drone_insert_hard_feasible", lambda *args, **kwargs: True
    )
    monkeypatch.setattr(operators, "record_local_drone_candidate", lambda _key: True)

    moves = operators._enumerate_feasible_drone_moves(customer, state, data, config)
    identities = {
        operators._regret_move_identity(customer, move, state) for move in moves
    }

    assert len(moves) > 1
    assert len(identities) > 1


def test_maximum_regret_customer_is_selected_and_its_best_move_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer_a, customer_b = data.customers[:2]
    state.unassigned = [customer_a, customer_b]
    applied = []

    def enumerate_moves(customer, *_args):
        moves = (
            [_van(10, 0), _van(11, 1)]
            if customer == customer_a
            else [_van(12, 0), _van(20, 1)]
        )
        return moves, _stats(moves)

    def apply_move(target, customer, move):
        applied.append((customer, move.cost))
        target.clean_unassigned(customer)

    monkeypatch.setattr(operators, "_enumerate_regret_moves", enumerate_moves)
    monkeypatch.setattr(operators, "_apply_move", apply_move)
    monkeypatch.setattr(operators, "_finalize_repair", lambda target, *_args: target)

    operators.regret_repair(state, np.random.default_rng(7), data, config)

    assert applied[0] == (customer_b, 12.0)


def test_remaining_customers_are_recomputed_after_each_insertion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer_a, customer_b = data.customers[:2]
    state.unassigned = [customer_a, customer_b]
    calls = []

    def enumerate_moves(customer, current_state, *_args):
        calls.append((customer, tuple(current_state.unassigned)))
        moves = (
            [_van(10, 0), _van(20, 1)]
            if customer == customer_a
            else [_van(10, 0), _van(11, 1)]
        )
        return moves, _stats(moves)

    monkeypatch.setattr(operators, "_enumerate_regret_moves", enumerate_moves)
    monkeypatch.setattr(
        operators,
        "_apply_move",
        lambda target, customer, _move: target.clean_unassigned(customer),
    )
    monkeypatch.setattr(operators, "_finalize_repair", lambda target, *_args: target)

    operators.regret_repair(state, np.random.default_rng(7), data, config)

    assert (customer_b, (customer_a, customer_b)) in calls
    assert (customer_b, (customer_b,)) in calls


def test_implementation_choice_single_candidate_has_structured_priority() -> None:
    single = operators.RegretEvaluation(
        5, [_van(100)], _van(100), None, None, 0, 1, 1, 0, 0.0, 0.0
    )
    multiple = operators.RegretEvaluation(
        6, [_van(1), _van(1000, 1)], _van(1), _van(1000, 1), 999.0,
        1, 2, 2, 0, 0.0, 0.0
    )
    assert min([multiple, single], key=operators._regret_customer_priority_key) is single


def test_multiple_single_candidate_tie_break_is_delta_order_then_customer() -> None:
    evaluations = [
        operators.RegretEvaluation(
            7, [_van(6)], _van(6), None, None, 0, 1, 1, 0, 0.0, 0.0
        ),
        operators.RegretEvaluation(
            6, [_van(5)], _van(5), None, None, 1, 1, 1, 0, 0.0, 0.0
        ),
        operators.RegretEvaluation(
            5, [_van(5)], _van(5), None, None, 0, 1, 1, 0, 0.0, 0.0
        ),
    ]
    ordered = sorted(evaluations, key=operators._regret_customer_priority_key)
    assert [evaluation.customer for evaluation in ordered] == [5, 6, 7]


def test_zero_candidate_preserves_existing_failure_behavior_without_pollution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer = data.customers[0]
    operators._remove_customer(state, customer)
    before = state.cache_signature()
    monkeypatch.setattr(
        operators,
        "_enumerate_regret_moves",
        lambda *_args: ([], _stats([])),
    )
    monkeypatch.setattr(operators, "_finalize_repair", lambda target, *_args: target)

    repaired = operators.regret_repair(
        state, np.random.default_rng(7), data, config
    )

    assert repaired.unassigned == [customer]
    assert state.cache_signature() == before


def test_move_identity_dedup_keeps_equal_cost_distinct_moves() -> None:
    _, data, state = _base_case(drone_enabled=False)
    customer = data.customers[0]
    first = _van(10, 0)
    duplicate = _van(10, 0)
    distinct_same_cost = _van(10, 1)

    unique = operators._deduplicate_regret_moves(
        customer, [first, duplicate, distinct_same_cost], state
    )

    assert len(unique) == 2
    assert {move.van_id for move in unique} == {"van_0", "van_1"}


def test_exact_delta_matches_full_objective_and_candidate_ranking() -> None:
    config, data, state, customer, _, _ = _cross_van_case()
    moves, _ = operators._enumerate_regret_moves(customer, state, data, config)
    van = next(move for move in moves if move.mode == "van")
    same = next(
        move
        for move in moves
        if move.mode == "drone"
        and move.sortie["launch_van_id"] == move.sortie["recovery_van_id"]
    )
    cross = next(
        move
        for move in moves
        if move.mode == "drone"
        and move.sortie["launch_van_id"] != move.sortie["recovery_van_id"]
    )
    base_cost, _ = objective(state.copy(), data, config)
    full_costs = []
    for move in (van, same, cross):
        candidate = state.copy()
        operators._apply_move(candidate, customer, operators._copy_move(move))
        full_cost, _ = objective(candidate, data, config)
        full_costs.append(full_cost)
        assert base_cost + move.cost == pytest.approx(full_cost)

    assert np.argsort([van.cost, same.cost, cross.cost]).tolist() == np.argsort(
        full_costs
    ).tolist()


def test_global_candidate_scope_does_not_use_regret_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer = data.customers[0]
    operators._remove_customer(state, customer)
    monkeypatch.setattr(
        operators,
        "_regret_customer_priority_key",
        lambda *_args: pytest.fail("Global called Regret ranking"),
    )
    move = operators._best_van_move(customer, state, data, config)
    assert move is not None


def test_local_remains_target_route_scoped() -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer = data.customers[0]
    operators._remove_customer(state, customer)
    traces = []

    operators.greedy_van_repair(
        state,
        np.random.default_rng(7),
        data,
        config,
        trace_collector=traces.append,
    )

    assert traces
    assert traces[0]["visited_van_ids"] == [traces[0]["target_van_id"]]


def test_cascade_does_not_call_regret_candidate_enumerator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, data, state = _base_case(drone_enabled=False)
    customer = data.customers[0]
    operators._remove_customer(state, customer)
    monkeypatch.setattr(
        operators,
        "_enumerate_regret_moves",
        lambda *_args: pytest.fail("Cascade called Regret enumeration"),
    )
    repaired = operators.cascade_repair(
        state, np.random.default_rng(7), data, config
    )
    assert customer not in repaired.unassigned


def test_regret_candidates_preserve_cross_van_recovery_and_full_feasibility() -> None:
    config, data, state, customer, launch_van, recovery_van = _cross_van_case()
    moves, _ = operators._enumerate_regret_moves(customer, state, data, config)
    cross = next(
        move
        for move in moves
        if move.mode == "drone"
        and move.sortie["launch_van_id"] == launch_van
        and move.sortie["recovery_van_id"] == recovery_van
    )
    operators._apply_move(state, customer, cross)
    feasible, violations = check_solution_feasible(state, data, config)
    assert feasible, violations


def test_regret_fixed_seed_is_deterministic_across_three_runs() -> None:
    config, data, state = _base_case()
    customers = state.van_routes["van_0"][1:3]
    for customer in customers:
        operators._remove_customer(state, customer)
    runs = []

    for _ in range(3):
        traces = []
        repaired = operators.regret_repair(
            state,
            np.random.default_rng(2026),
            data,
            config,
            trace_collector=traces.append,
        )
        semantic_trace = [
            (
                row["round"],
                row["customer_id"],
                row["raw_candidate_count"],
                row["unique_candidate_count"],
                row["best_move_identity"],
                row["best_delta"],
                row["second_move_identity"],
                row["second_delta"],
                row["regret"],
                row["selected_customer"],
            )
            for row in traces
        ]
        runs.append(
            (
                semantic_trace,
                repaired.cache_signature(),
                objective(repaired, data, config)[0],
            )
        )

    assert runs[0] == runs[1] == runs[2]


def test_successful_regret_repair_final_state_is_fully_feasible() -> None:
    config, data, state = _base_case()
    customers = state.van_routes["van_0"][1:3]
    for customer in customers:
        operators._remove_customer(state, customer)

    repaired = operators.regret_repair(
        state, np.random.default_rng(2026), data, config
    )
    feasible, violations = check_solution_feasible(repaired, data, config)
    served = repaired.get_van_customers() + repaired.get_drone_customers()
    counts = Counter(served)

    assert feasible, violations
    assert repaired.unassigned == []
    assert set(served) == set(data.customers)
    assert all(counts[customer] == 1 for customer in data.customers)


def test_true_regret2_differs_from_old_mode_level_regret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = _evaluate_synthetic(
        monkeypatch, [_van(10, 0), _van(11, 1), _drone(30, 0)]
    )
    old_mode_level_regret = 30.0 - 10.0
    assert evaluation.regret == pytest.approx(1.0)
    assert evaluation.regret != pytest.approx(old_mode_level_regret)
