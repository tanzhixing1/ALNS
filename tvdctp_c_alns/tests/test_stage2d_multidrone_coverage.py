from __future__ import annotations

from collections import defaultdict

import pytest

import operators
from feasibility import check_solution_feasible
from objective import objective
from test_stage2d0_cascade_contract import (
    FixedChoiceRng,
    _coordinated_fixture,
    _set_destroy_count,
)


def _idle_multidrone_state():
    config, data, source, ids = _coordinated_fixture()
    state = source.copy()
    target = ids["plain_van_customer"]
    other_van_customers = [
        customer
        for customer in data.customers
        if customer
        not in {
            ids["same_anchor"],
            ids["recovery_anchor"],
            ids["same_drone_customer"],
            ids["cross_drone_customer"],
            target,
        }
    ]
    state.van_routes = {
        ids["launch_van"]: [
            state.selected_transshipment,
            ids["same_anchor"],
            ids["same_drone_customer"],
            *other_van_customers,
            state.selected_transshipment,
        ],
        ids["recovery_van"]: [
            state.selected_transshipment,
            ids["recovery_anchor"],
            ids["cross_drone_customer"],
            state.selected_transshipment,
        ],
    }
    state.sync_primary_van_route()
    state.drone_sorties = []
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[target] = "unassigned"
    state.unassigned = [target]
    feasible, violations = check_solution_feasible(state.copy(), data, config)
    assert feasible is False
    assert violations == [f"unassigned customers remain: [{target}]"]
    return config, data, state, ids, target


def _warehouse_return_counterexample():
    config, data, state, ids, target = _idle_multidrone_state()
    served = ids["same_drone_customer"]
    state.van_routes[ids["launch_van"]].remove(served)
    state.sync_primary_van_route()
    sortie = operators._make_drone_sortie(
        state.selected_transshipment,
        [served],
        state.selected_transshipment,
        drone_id=ids["same_drone_id"],
        launch_van_id=ids["launch_van"],
        recovery_van_id=ids["recovery_van"],
    )
    sortie["launch_position"] = 0
    sortie["recovery_position"] = len(state.van_routes[ids["recovery_van"]]) - 1
    state.drone_sorties = [sortie]
    state.service_mode[served] = "drone"
    feasible, violations = check_solution_feasible(state.copy(), data, config)
    assert feasible is False
    assert violations == [f"unassigned customers remain: [{target}]"]
    return config, data, state, ids, target


def _move_key(move):
    sortie = move.sortie or {}
    launch, customers, recovery = operators.sortie_nodes(sortie)
    return (
        str(sortie.get("launch_van_id", "")),
        int(launch),
        int(sortie.get("launch_position", -1)),
        str(sortie.get("recovery_van_id", "")),
        int(recovery),
        int(sortie.get("recovery_position", -1)),
        tuple(int(customer) for customer in customers),
    )


def _apply_drone_move(state, target, move):
    candidate = state.copy()
    operators._apply_move(candidate, target, operators._copy_move(move))
    return candidate


def test_two_idle_symmetric_drones_are_both_enumerated_without_pruning() -> None:
    config, data, state, ids, target = _idle_multidrone_state()
    moves = operators._enumerate_feasible_drone_moves_for_customers(
        [target], state, data, config
    )
    by_drone = defaultdict(dict)
    for move in moves:
        sortie = move.sortie or {}
        if sortie.get("launch_van_id") == ids["launch_van"]:
            by_drone[str(sortie.get("drone_id"))][_move_key(move)] = move

    first_id = ids["same_drone_id"]
    second_id = ids["cross_drone_id"]
    common = sorted(set(by_drone[first_id]).intersection(by_drone[second_id]), key=repr)
    assert common
    first = by_drone[first_id][common[0]]
    second = by_drone[second_id][common[0]]
    assert first.cost == pytest.approx(second.cost)

    first_state = _apply_drone_move(state, target, first)
    second_state = _apply_drone_move(state, target, second)
    assert check_solution_feasible(first_state, data, config) == (True, [])
    assert check_solution_feasible(second_state, data, config) == (True, [])
    assert objective(first_state, data, config)[0] == pytest.approx(
        objective(second_state, data, config)[0]
    )

    first_identity = operators._regret_move_identity(target, first, state)
    second_identity = operators._regret_move_identity(target, second, state)
    assert first_identity != second_identity
    assert first_identity[:2] + first_identity[3:] == (
        second_identity[:2] + second_identity[3:]
    )


def test_first_drone_warehouse_returned_second_drone_candidate_is_found() -> None:
    config, data, state, ids, target = _warehouse_return_counterexample()
    assert operators._first_drone_for_van(state, ids["launch_van"]) == ids[
        "same_drone_id"
    ]

    moves = operators._enumerate_feasible_drone_moves_for_customers(
        [target], state, data, config
    )
    move_ids = {str((move.sortie or {}).get("drone_id")) for move in moves}
    assert ids["same_drone_id"] not in move_ids
    assert ids["cross_drone_id"] in move_ids

    second_move = next(
        move
        for move in moves
        if (move.sortie or {}).get("drone_id") == ids["cross_drone_id"]
    )
    assert check_solution_feasible(
        _apply_drone_move(state, target, second_move), data, config
    ) == (True, [])


def test_first_drone_has_existing_sortie_second_idle_drone_is_retained() -> None:
    config, data, state, ids, target = _idle_multidrone_state()
    served = ids["same_drone_customer"]
    state.van_routes[ids["launch_van"]].remove(served)
    state.sync_primary_van_route()
    anchor = ids["same_anchor"]
    sortie = operators._make_drone_sortie(
        state.selected_transshipment,
        [served],
        anchor,
        drone_id=ids["same_drone_id"],
        launch_van_id=ids["launch_van"],
        recovery_van_id=ids["launch_van"],
    )
    sortie["launch_position"] = 0
    sortie["recovery_position"] = state.van_routes[ids["launch_van"]].index(anchor)
    state.drone_sorties = [sortie]
    state.service_mode[served] = "drone"

    moves = operators._enumerate_feasible_drone_moves_for_customers(
        [target], state, data, config
    )
    assert any(
        (move.sortie or {}).get("drone_id") == ids["cross_drone_id"]
        for move in moves
    )


def test_cross_van_recovery_updates_current_carrier_for_enumeration() -> None:
    config, data, state, ids, target = _idle_multidrone_state()
    served = ids["same_drone_customer"]
    state.van_routes[ids["launch_van"]].remove(served)
    state.sync_primary_van_route()
    recovery = ids["recovery_anchor"]
    sortie = operators._make_drone_sortie(
        state.selected_transshipment,
        [served],
        recovery,
        drone_id=ids["same_drone_id"],
        launch_van_id=ids["launch_van"],
        recovery_van_id=ids["recovery_van"],
    )
    sortie["launch_position"] = 0
    sortie["recovery_position"] = state.van_routes[ids["recovery_van"]].index(
        recovery
    )
    state.drone_sorties = [sortie]
    state.service_mode[served] = "drone"

    candidates = operators._candidate_drones_for_launch_van(
        state, ids["recovery_van"]
    )
    assert ids["same_drone_id"] in candidates
    assert ids["cross_drone_id"] not in candidates

    moves = operators._enumerate_feasible_drone_moves_for_customers(
        [target], state, data, config
    )
    transferred = [
        move
        for move in moves
        if (move.sortie or {}).get("drone_id") == ids["same_drone_id"]
        and (move.sortie or {}).get("launch_van_id") == ids["recovery_van"]
    ]
    assert transferred
    assert any(
        check_solution_feasible(
            _apply_drone_move(state, target, move), data, config
        )
        == (True, [])
        for move in transferred
    )


def test_nonfirst_drone_preserves_cross_van_recovery_candidates() -> None:
    config, data, state, ids, target = _warehouse_return_counterexample()
    moves = operators._enumerate_feasible_drone_moves_for_customers(
        [target], state, data, config
    )
    assert any(
        (move.sortie or {}).get("drone_id") == ids["cross_drone_id"]
        and (move.sortie or {}).get("launch_van_id") == ids["launch_van"]
        and (move.sortie or {}).get("recovery_van_id") == ids["recovery_van"]
        for move in moves
    )


def test_stage2c_regret_retains_nonfirst_feasible_drone() -> None:
    config, data, state, ids, target = _warehouse_return_counterexample()
    moves, diagnostics = operators._enumerate_regret_moves(
        target, state, data, config
    )
    assert diagnostics["drone_candidate_count"] > 0
    assert any(
        move.mode == "drone"
        and (move.sortie or {}).get("drone_id") == ids["cross_drone_id"]
        for move in moves
    )


def test_stage2d_whole_bundle_retains_nonfirst_feasible_drone() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )
    bundle = destroyed.metadata["cascade_bundles"][0]
    assert bundle.customer_ids == (
        ids["recovery_anchor"],
        ids["cross_drone_customer"],
    )

    existing = destroyed.drone_sorties[0]
    existing["launch"] = destroyed.selected_transshipment
    existing["launch_van_id"] = ids["launch_van"]
    existing["launch_position"] = 0
    existing["recovery"] = destroyed.selected_transshipment
    existing["recovery_van_id"] = ids["recovery_van"]
    existing["recovery_position"] = len(
        destroyed.van_routes[ids["recovery_van"]]
    ) - 1
    existing["same_node"] = True

    states = operators._drone_bundle_strategy_states(
        destroyed,
        bundle,
        data,
        config,
        {"state_copy_count": 0},
    )
    matching = [
        candidate
        for candidate in states
        if any(
            operators.sortie_nodes(sortie)[1] == list(bundle.dependency_order)
            and sortie.get("drone_id") == ids["cross_drone_id"]
            for sortie in candidate.drone_sorties
            if isinstance(sortie, dict)
        )
    ]
    assert matching
    assert check_solution_feasible(matching[0], data, config) == (True, [])
