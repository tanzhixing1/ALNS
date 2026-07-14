from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import operators
from feasibility import check_solution_feasible
from objective import objective
from state import AffectedStructureScope, CascadeBundleSnapshot
from test_stage2d0_cascade_contract import (
    FixedChoiceRng,
    _coordinated_fixture,
    _set_destroy_count,
)


def _destroy(source, config, data, selected):
    _set_destroy_count(config, data, len(selected))
    return operators.cascade_aware_removal(
        source,
        FixedChoiceRng(selected),
        data,
        config,
    )


def _repair(destroyed, data, config, seed: int = 17):
    return operators.cascade_repair(
        destroyed,
        np.random.default_rng(seed),
        data,
        config,
    )


def _diagnostics(state):
    return state.metadata["cascade_repair_diagnostics"]


def _refresh_first_bundle(destroyed, replacement: CascadeBundleSnapshot):
    mutated = destroyed.copy()
    mutated.metadata["cascade_bundles"][0] = replacement
    mutated.metadata["cascade_contract"]["bundle_ids"] = tuple(
        bundle.bundle_id for bundle in mutated.metadata["cascade_bundles"]
    )
    mutated.metadata["cascade_contract"]["bundle_fingerprints"] = tuple(
        bundle.contract_fingerprint()
        for bundle in mutated.metadata["cascade_bundles"]
    )
    return mutated


def _enumerate_one(destroyed, bundle, data, config):
    metrics = {
        "state_copy_count": 0,
        "checker_call_count": 0,
        "objective_call_count": 0,
    }
    allowed = set(destroyed.unassigned) - set(bundle.customer_ids)
    return operators._enumerate_bundle_reconstruction_strategies(
        destroyed,
        bundle,
        allowed_unassigned=allowed,
        data=data,
        config=config,
        metrics=metrics,
    )


def test_git_provenance_gate_is_pass() -> None:
    report = (
        Path(__file__).parents[1]
        / "outputs"
        / "stage2d1_cascade_repair_audit"
        / "00_git_provenance.md"
    ).read_text(encoding="utf-8")

    assert "GIT PROVENANCE PASS" in report
    assert "GIT PROVENANCE FAIL" not in report


def test_bundle_only_scope_leaves_external_unassigned_untouched(monkeypatch) -> None:
    config, data, source, ids = _coordinated_fixture()
    external = next(
        customer
        for customer in data.customers
        if customer
        not in {
            ids["plain_van_customer"],
            ids["same_drone_customer"],
            ids["cross_drone_customer"],
            ids["same_anchor"],
            ids["recovery_anchor"],
        }
    )
    operators._remove_customer(source, external)
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])

    monkeypatch.setattr(
        operators,
        "_finish_repair",
        lambda *args, **kwargs: pytest.fail("global completion called"),
    )
    repaired = _repair(destroyed, data, config)

    assert ids["plain_van_customer"] not in repaired.unassigned
    assert repaired.unassigned == [external]
    assert _diagnostics(repaired)["status"] == "success"


def test_first_bundle_does_not_consume_later_bundle(monkeypatch) -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(
        source,
        config,
        data,
        [ids["same_drone_customer"], ids["cross_drone_customer"]],
    )
    bundles = destroyed.metadata["cascade_bundles"]
    calls = []
    original = operators._enumerate_bundle_reconstruction_strategies

    def recording(state, bundle, **kwargs):
        calls.append((bundle.bundle_id, tuple(state.unassigned)))
        return original(state, bundle, **kwargs)

    monkeypatch.setattr(
        operators, "_enumerate_bundle_reconstruction_strategies", recording
    )
    repaired = _repair(destroyed, data, config)

    assert [item[0] for item in calls] == [bundle.bundle_id for bundle in bundles]
    assert set(bundles[1].customer_ids).issubset(set(calls[0][1]))
    assert set(bundles[1].customer_ids).issubset(set(calls[1][1]))
    assert repaired.unassigned == []


def test_multiple_bundles_preserve_stable_removal_order_across_three_runs() -> None:
    config, data, source, ids = _coordinated_fixture()
    results = []
    for _ in range(3):
        destroyed = _destroy(
            source,
            config,
            data,
            [ids["same_drone_customer"], ids["cross_drone_customer"]],
        )
        repaired = _repair(destroyed, data, config, seed=31)
        diagnostics = _diagnostics(repaired)
        results.append(
            (
                diagnostics["bundle_processing_sequence"],
                [
                    row["strategy_generation_sequence"]
                    for row in diagnostics["bundles"]
                ],
                diagnostics["result_state_fingerprint"],
            )
        )

    assert results[0] == results[1] == results[2]


def test_bundle_external_served_structure_projection_is_unchanged() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    bundle_customers = set(destroyed.metadata["cascade_removed"])
    before = operators._external_structure_projection(source, bundle_customers)

    repaired = _repair(destroyed, data, config)
    after = operators._external_structure_projection(repaired, bundle_customers)

    assert after == before


def test_missing_metadata_fails_without_any_repair_fallback(monkeypatch) -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    operators._clear_stale_cascade_metadata(destroyed)
    before = operators._state_business_fingerprint(destroyed)

    def forbidden(*args, **kwargs):
        pytest.fail("repair fallback called")

    for name in (
        "greedy_van_repair",
        "greedy_drone_repair",
        "best_mode_repair",
        "regret_repair",
        "_finish_repair",
        "_all_moves",
    ):
        monkeypatch.setattr(operators, name, forbidden)

    repaired = _repair(destroyed, data, config)

    assert operators._state_business_fingerprint(destroyed) == before
    assert operators._state_business_fingerprint(repaired) == before
    assert _diagnostics(repaired)["status"] == "failure"


@pytest.mark.parametrize(
    "mutation",
    ["schema", "source", "revision", "missing_snapshot", "invalid_scope"],
)
def test_invalid_metadata_fails_atomically(mutation: str) -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    if mutation == "schema":
        destroyed.metadata["cascade_contract"]["schema_version"] = 999
    elif mutation == "source":
        destroyed.metadata["cascade_contract"]["source_operator"] = "wrong"
    else:
        bundle = destroyed.metadata["cascade_bundles"][0]
        if mutation == "revision":
            replacement = replace(bundle, source_destroy_call_id="wrong")
        elif mutation == "missing_snapshot":
            replacement = replace(bundle, customer_service_snapshots=())
        else:
            bad_scope = replace(
                bundle.affected_structure_scope,
                van_route_segment_ids=("van:outside:0-1",),
            )
            replacement = replace(bundle, affected_structure_scope=bad_scope)
        destroyed = _refresh_first_bundle(destroyed, replacement)
    before = operators._state_business_fingerprint(destroyed)

    repaired = _repair(destroyed, data, config)

    assert _diagnostics(repaired)["status"] == "failure"
    assert operators._state_business_fingerprint(repaired) == before
    assert operators._state_business_fingerprint(destroyed) == before


def test_snapshot_candidate_is_a_complete_bundle_strategy() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["cross_drone_customer"]])
    bundle = destroyed.metadata["cascade_bundles"][0]

    strategies, _ = _enumerate_one(destroyed, bundle, data, config)
    strategy = next(item for item in strategies if item.source_kind == "snapshot")

    assert {item[0] for item in strategy.service_mode_reconstruction} == set(
        bundle.customer_ids
    )
    assert strategy.van_route_segment_reconstruction
    assert strategy.drone_subroute_reconstruction
    assert strategy.launch_recovery_reconstruction
    assert strategy.carrier_transfer_reconstruction
    assert set(bundle.customer_ids).isdisjoint(strategy.resulting_state.unassigned)


def test_complete_objective_selects_lower_bundle_strategy() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    bundle = destroyed.metadata["cascade_bundles"][0]
    strategies, _ = _enumerate_one(destroyed, bundle, data, config)
    assert len(strategies) >= 2
    strategies[0].objective_value = 100.0
    strategies[1].objective_value = 105.0

    assert operators._select_bundle_strategy(strategies[:2]) is strategies[0]


def test_exact_objective_tie_uses_stable_full_identity() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    bundle = destroyed.metadata["cascade_bundles"][0]
    strategies, _ = _enumerate_one(destroyed, bundle, data, config)
    first, second = strategies[:2]
    assert first.stable_identity() != second.stable_identity()
    first.objective_value = second.objective_value = 100.0
    expected = min((first, second), key=lambda item: item.stable_identity())

    selected = [
        operators._select_bundle_strategy(order)
        for order in ([first, second], [second, first], [first, second])
    ]

    assert selected == [expected, expected, expected]
    assert len(
        {
            operators._state_business_fingerprint(item.resulting_state)
            for item in selected
            if item is not None
        }
    ) == 1


def test_equal_cost_different_strategies_are_not_deduplicated_by_cost() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    bundle = destroyed.metadata["cascade_bundles"][0]
    strategies, row = _enumerate_one(destroyed, bundle, data, config)
    first, second = strategies[:2]
    first.objective_value = second.objective_value = 88.0

    assert first.stable_identity() != second.stable_identity()
    assert len([first, second]) == 2
    assert row["unique_bundle_strategy_count"] >= 2


def test_later_empty_strategy_set_rolls_back_earlier_bundle(monkeypatch) -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(
        source,
        config,
        data,
        [ids["same_drone_customer"], ids["cross_drone_customer"]],
    )
    input_fingerprint = operators._state_business_fingerprint(destroyed)
    second_id = destroyed.metadata["cascade_bundles"][1].bundle_id
    original = operators._enumerate_bundle_reconstruction_strategies

    def fail_second(state, bundle, **kwargs):
        if bundle.bundle_id == second_id:
            return [], {
                "bundle_id": bundle.bundle_id,
                "bundle_size": len(bundle.customer_ids),
                "affected_route_segment_count": len(bundle.affected_route_segments),
                "affected_drone_subroute_count": len(bundle.removed_drone_subroutes),
                "raw_bundle_strategy_count": 0,
                "feasible_bundle_strategy_count": 0,
                "unique_bundle_strategy_count": 0,
                "strategy_generation_sequence": [],
                "rejection_reasons": ["forced empty"],
                "enumeration_time": 0.0,
            }
        return original(state, bundle, **kwargs)

    monkeypatch.setattr(
        operators, "_enumerate_bundle_reconstruction_strategies", fail_second
    )
    repaired = _repair(destroyed, data, config)

    assert _diagnostics(repaired)["status"] == "failure"
    assert operators._state_business_fingerprint(repaired) == input_fingerprint
    assert operators._state_business_fingerprint(destroyed) == input_fingerprint


def test_cascade_does_not_call_other_repair_or_global_helpers(monkeypatch) -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])

    def forbidden(*args, **kwargs):
        pytest.fail("forbidden fallback/global helper called")

    for name in (
        "greedy_van_repair",
        "greedy_drone_repair",
        "best_mode_repair",
        "regret_repair",
        "_finish_repair",
        "_all_moves",
        "consolidate_drone_sorties",
    ):
        monkeypatch.setattr(operators, name, forbidden)

    repaired = _repair(destroyed, data, config)

    assert _diagnostics(repaired)["status"] == "success"


def test_partial_validation_ignores_only_explicit_external_missing_service(
    monkeypatch,
) -> None:
    config, data, source, _ = _coordinated_fixture()
    external = data.customers[-1]
    operators._remove_customer(source, external)
    metrics = {}
    original_checker = operators.check_solution_feasible
    calls = []

    def recording_checker(*args, **kwargs):
        calls.append(1)
        return original_checker(*args, **kwargs)

    monkeypatch.setattr(operators, "check_solution_feasible", recording_checker)
    valid, violations = operators._validate_cascade_candidate(
        source,
        bundle_customers=set(),
        allowed_unassigned={external},
        data=data,
        config=config,
        metrics=metrics,
    )
    missing_bundle_valid, missing_bundle_violations = (
        operators._validate_cascade_candidate(
            source,
            bundle_customers={external},
            allowed_unassigned=set(),
            data=data,
            config=config,
            metrics=metrics,
        )
    )

    assert valid is True, violations
    assert missing_bundle_valid is False
    assert missing_bundle_violations
    assert len(calls) == 2


@pytest.mark.parametrize(
    "violation",
    [
        "customers served more than once: [5]",
        "customer 5 violates time window",
        "van payload capacity exceeded.",
        "drone battery capacity exceeded",
        "drone carrier synchronization failed",
    ],
)
def test_partial_validation_never_ignores_non_missing_service_violation(
    monkeypatch, violation: str
) -> None:
    config, data, source, _ = _coordinated_fixture()
    monkeypatch.setattr(
        operators,
        "check_solution_feasible",
        lambda *args, **kwargs: (False, [violation]),
    )

    valid, retained = operators._validate_cascade_candidate(
        source,
        bundle_customers=set(),
        allowed_unassigned=set(),
        data=data,
        config=config,
        metrics={},
    )

    assert valid is False
    assert retained == [violation]


def test_full_checker_semantics_remain_strict() -> None:
    config, data, source, _ = _coordinated_fixture()
    feasible, violations = check_solution_feasible(source.copy(), data, config)
    broken = source.copy()
    customer = data.customers[0]
    operators._remove_customer(broken, customer)
    broken.unassigned = []
    broken_feasible, broken_violations = check_solution_feasible(broken, data, config)

    assert feasible is True, violations
    assert broken_feasible is False
    assert any("missing from served/unassigned" in item for item in broken_violations)


def test_cross_van_snapshot_reconstruction_is_supported_and_feasible() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["cross_drone_customer"]])
    bundle = destroyed.metadata["cascade_bundles"][0]
    strategies, _ = _enumerate_one(destroyed, bundle, data, config)
    snapshot = next(item for item in strategies if item.source_kind == "snapshot")
    cross = next(
        sortie
        for sortie in snapshot.resulting_state.drone_sorties
        if ids["cross_drone_customer"] in sortie.get("customers", [])
    )
    feasible, violations = check_solution_feasible(
        snapshot.resulting_state, data, config
    )

    assert cross["launch_van_id"] == ids["launch_van"]
    assert cross["recovery_van_id"] == ids["recovery_van"]
    assert cross["launch_van_id"] != cross["recovery_van_id"]
    assert feasible is True, violations


def test_unrelated_sortie_is_not_modified_by_cascade_consolidation() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    bundle_customers = set(destroyed.metadata["cascade_removed"])
    original_sorties = tuple(
        operators._sortie_structural_identity(sortie)
        for sortie in source.drone_sorties
        if bundle_customers.isdisjoint(operators.sortie_nodes(sortie)[1])
    )

    repaired = _repair(destroyed, data, config)
    repaired_sorties = tuple(
        operators._sortie_structural_identity(sortie)
        for sortie in repaired.drone_sorties
        if bundle_customers.isdisjoint(operators.sortie_nodes(sortie)[1])
    )

    assert repaired_sorties == original_sorties


def test_repair_uses_pre_destroy_snapshot_instead_of_guessing_relations() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["cross_drone_customer"]])
    bundle = destroyed.metadata["cascade_bundles"][0]
    assert ids["cross_drone_customer"] not in destroyed.get_drone_customers()

    restored = operators._restore_snapshot_strategy_state(
        destroyed, bundle, {"state_copy_count": 0}
    )

    assert restored is not None
    restored_cross = next(
        sortie
        for sortie in restored.drone_sorties
        if ids["cross_drone_customer"] in sortie.get("customers", [])
    )
    assert restored_cross["drone_id"] == ids["cross_drone_id"]
    assert restored_cross["launch_van_id"] == ids["launch_van"]
    assert restored_cross["recovery_van_id"] == ids["recovery_van"]


def test_metadata_is_consumed_and_consecutive_cycles_do_not_chain() -> None:
    config, data, source, ids = _coordinated_fixture()
    first_destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    first_repaired = _repair(first_destroyed, data, config)

    assert all(key not in first_repaired.metadata for key in operators.CASCADE_METADATA_KEYS)
    copied = first_repaired.copy()
    copied.metadata["cascade_repair_diagnostics"]["status"] = "copy-only"
    assert _diagnostics(first_repaired)["status"] == "success"

    second_destroyed = _destroy(
        first_repaired, config, data, [ids["same_drone_customer"]]
    )
    second_repaired = _repair(second_destroyed, data, config)

    assert _diagnostics(second_repaired)["status"] == "success"
    assert all(key not in second_repaired.metadata for key in operators.CASCADE_METADATA_KEYS)


def test_fixed_seed_diagnostics_are_deterministic_across_three_runs() -> None:
    config, data, source, ids = _coordinated_fixture()
    rows = []
    for _ in range(3):
        destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
        repaired = _repair(destroyed, data, config, seed=101)
        diagnostics = _diagnostics(repaired)
        rows.append(
            (
                diagnostics["bundle_processing_sequence"],
                [row["raw_bundle_strategy_count"] for row in diagnostics["bundles"]],
                [row["unique_bundle_strategy_count"] for row in diagnostics["bundles"]],
                [row["selected_strategy_identity"] for row in diagnostics["bundles"]],
                [row["selected_objective"] for row in diagnostics["bundles"]],
                diagnostics["result_state_fingerprint"],
                check_solution_feasible(repaired, data, config),
            )
        )

    assert rows[0] == rows[1] == rows[2]


def test_complexity_hard_canaries_are_recorded_and_deterministic() -> None:
    config, data, source, ids = _coordinated_fixture()
    canaries = []
    for _ in range(2):
        destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
        diagnostics = _diagnostics(_repair(destroyed, data, config))
        row = diagnostics["bundles"][0]
        canaries.append(
            (
                row["bundle_size"],
                row["affected_route_segment_count"],
                row["affected_drone_subroute_count"],
                row["raw_bundle_strategy_count"],
                row["unique_bundle_strategy_count"],
                diagnostics["state_copy_count"],
                diagnostics["objective_call_count"],
                diagnostics["checker_call_count"],
                diagnostics["maximum_reconstruction_depth"],
            )
        )

    assert canaries[0] == canaries[1]
    assert all(isinstance(value, int) and value >= 0 for value in canaries[0])
    assert canaries[0][-1] == 1


def test_timing_metrics_are_soft_nonnegative_diagnostics() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(source, config, data, [ids["plain_van_customer"]])
    diagnostics = _diagnostics(_repair(destroyed, data, config))

    assert diagnostics["enumeration_time"] >= 0.0
    assert diagnostics["scoring_time"] >= 0.0
    assert diagnostics["bundle_repair_time"] >= 0.0
    assert diagnostics["bundles"][0]["enumeration_time"] >= 0.0


def test_no_customer_compositional_explosion_or_lossy_pruning() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(
        source,
        config,
        data,
        [ids["same_drone_customer"], ids["cross_drone_customer"]],
    )
    diagnostics = _diagnostics(_repair(destroyed, data, config))

    assert diagnostics["customer_compositional_product_used"] is False
    assert diagnostics["lossy_pruning_used"] is False
    assert all(
        row["unique_bundle_strategy_count"] <= row["raw_bundle_strategy_count"]
        for row in diagnostics["bundles"]
    )


def test_all_bundles_success_produces_full_feasible_state_and_objective() -> None:
    config, data, source, ids = _coordinated_fixture()
    destroyed = _destroy(
        source,
        config,
        data,
        [ids["same_drone_customer"], ids["cross_drone_customer"]],
    )

    repaired = _repair(destroyed, data, config)
    feasible, violations = check_solution_feasible(repaired, data, config)
    total, breakdown = objective(repaired, data, config)

    assert _diagnostics(repaired)["status"] == "success"
    assert repaired.unassigned == []
    assert feasible is True, violations
    assert total == pytest.approx(breakdown["total_cost"])
    assert total > 0.0
