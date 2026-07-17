from __future__ import annotations

import hashlib
from dataclasses import replace

import numpy as np
import pytest

import operators
import ordinary_cascade_adapter as adapter
from feasibility import check_solution_feasible
from objective import objective
from removal_structural_context import (
    ACTIVE_REMOVAL_CONTEXT_KEY,
    active_removal_context,
    detach_active_removal_context,
)
from tests.test_stage2d0_cascade_contract import (
    FixedChoiceRng,
    _coordinated_fixture,
    _set_destroy_count,
)
from tests.test_stage2ea1_structural_context import (
    CANDIDATE_TRACE_BASELINE,
    PAIR_BASELINE,
    _business_fingerprint,
    _stable_diagnostic,
)


ORDINARY_DESTROYS = (
    ("Random", operators.random_customer_removal),
    ("Greedy", operators.greedy_removal),
    ("Related", operators.related_customer_removal),
)


def _stable_without_timing(value):
    if isinstance(value, dict):
        return tuple(
            (key, _stable_without_timing(item))
            for key, item in sorted(value.items())
            if not (key.endswith("_time") or "seconds" in key)
        )
    if isinstance(value, list):
        return tuple(_stable_without_timing(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_stable_without_timing(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_stable_without_timing(item) for item in value))
    return value


def _adapt(destroy, *, selected=None, count=1):
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, count)
    rng = FixedChoiceRng(selected) if selected is not None else np.random.default_rng(29)
    destroyed = destroy(source, rng, data, config)
    context = active_removal_context(destroyed)
    assert context is not None
    bundles = adapter.adapt_removal_context_to_cascade_bundles(context, destroyed)
    return config, data, source, ids, destroyed, context, bundles


def _empty_row(bundle):
    return {
        "bundle_id": bundle.bundle_id,
        "bundle_size": len(bundle.customer_ids),
        "affected_route_segment_count": len(bundle.affected_route_segments),
        "affected_drone_subroute_count": len(bundle.removed_drone_subroutes),
        "raw_bundle_strategy_count": 0,
        "feasible_bundle_strategy_count": 0,
        "unique_bundle_strategy_count": 0,
        "strategy_generation_sequence": [],
        "rejection_reasons": [],
        "enumeration_time": 0.0,
    }


def _same_drone_fixture(*, transferred: bool):
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    first = dict(source.drone_sorties[0])
    second = dict(source.drone_sorties[1])
    first.update(
        {
            "drone_id": "drone_0",
            "launch_van_id": "van_0",
            "recovery_van_id": "van_1" if transferred else "van_0",
            "launch": 5,
            "recovery": 6 if transferred else 5,
            "launch_position": 1,
            "recovery_position": 1,
            "customers": [7],
        }
    )
    second.update(
        {
            "drone_id": "drone_0",
            "launch_van_id": "van_1",
            "recovery_van_id": "van_1",
            "launch": 6,
            "recovery": 6,
            "launch_position": 1,
            "recovery_position": 1,
            "customers": [8],
        }
    )
    source.drone_sorties = [first, second]
    source.service_mode[7] = "drone"
    source.service_mode[8] = "drone"
    destroyed = operators.random_customer_removal(
        source, FixedChoiceRng([7, 8]), data, config
    )
    context = active_removal_context(destroyed)
    bundles = adapter.adapt_removal_context_to_cascade_bundles(context, destroyed)
    return config, data, source, destroyed, context, bundles


def test_actual_r_not_selected_drives_partition_and_no_state_expansion() -> None:
    config, data, source, ids, destroyed, context, bundles = _adapt(
        operators.random_customer_removal,
        selected=[5],
    )

    assert context.selected_removed_customer_ids == (5,)
    assert context.actually_unassigned_customer_ids == (5, 7)
    assert {customer for bundle in bundles for customer in bundle.customer_ids} == {5, 7}
    assert destroyed.unassigned == [5, 7]
    assert source.unassigned == []


def test_singleton_van_bundle_has_exact_snapshot_and_boundary() -> None:
    _, _, _, _, _, context, bundles = _adapt(
        operators.random_customer_removal,
        selected=[10],
    )

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle.customer_ids == (10,)
    assert bundle.dependency_order == (10,)
    assert bundle.affected_route_segments[0].route_nodes == (9, 10, 11)
    assert context.external_boundary_entities.customer_ids == (9, 11)


def test_contiguous_van_block_merges_and_uses_route_order() -> None:
    _, _, _, _, _, _, bundles = _adapt(
        operators.random_customer_removal,
        selected=[9, 10],
        count=2,
    )

    assert len(bundles) == 1
    assert bundles[0].customer_ids == (9, 10)
    assert bundles[0].dependency_order == (9, 10)


def test_same_route_noncontiguous_customers_do_not_merge() -> None:
    _, _, _, _, _, _, bundles = _adapt(
        operators.random_customer_removal,
        selected=[9, 11],
        count=2,
    )

    assert tuple(bundle.customer_ids for bundle in bundles) == ((9,), (11,))


def test_dependency_order_is_structural_not_customer_id_order() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    source.van_routes["van_0"] = [3, 5, 10, 9, 11, 12, 3]
    source.sync_primary_van_route()
    destroyed = operators.random_customer_removal(
        source, FixedChoiceRng([10, 9]), data, config
    )
    context = active_removal_context(destroyed)
    bundles = adapter.adapt_removal_context_to_cascade_bundles(context, destroyed)

    assert context.actually_unassigned_customer_ids == (9, 10)
    assert bundles[0].dependency_order == (10, 9)


def test_full_removed_sortie_is_one_bundle_and_partial_is_not_produced() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    source.drone_sorties[0]["customers"] = [7, 9]
    source.van_routes["van_0"] = [
        node for node in source.van_routes["van_0"] if node != 9
    ]
    source.sync_primary_van_route()
    source.service_mode[9] = "drone"
    destroyed = operators.random_customer_removal(
        source, FixedChoiceRng([7]), data, config
    )
    context = active_removal_context(destroyed)
    bundles = adapter.adapt_removal_context_to_cascade_bundles(context, destroyed)

    assert context.selected_removed_customer_ids == (7,)
    assert context.actually_unassigned_customer_ids == (7, 9)
    assert len(bundles) == 1
    assert bundles[0].dependency_order == (7, 9)
    assert bundles[0].removed_drone_subroutes[0].customer_ids == (7, 9)


def test_same_drone_without_direct_transfer_does_not_connect_sorties() -> None:
    _, _, _, _, _, bundles = _same_drone_fixture(transferred=False)

    assert tuple(bundle.customer_ids for bundle in bundles) == ((7,), (8,))


def test_direct_carrier_transfer_connects_adjacent_removed_sorties() -> None:
    _, _, _, _, _, bundles = _same_drone_fixture(transferred=True)

    assert len(bundles) == 1
    assert bundles[0].dependency_order == (7, 8)
    assert any(
        ":edge:carrier-transfer:" in edge
        for edge in bundles[0].affected_structure_scope.coordination_edge_ids
    )


def test_real_launch_anchor_connects_but_unrelated_customer_does_not() -> None:
    _, _, _, _, _, _, anchor_bundles = _adapt(
        operators.random_customer_removal,
        selected=[5],
    )
    _, _, _, _, _, _, unrelated_bundles = _adapt(
        operators.random_customer_removal,
        selected=[7, 10],
        count=2,
    )

    assert len(anchor_bundles) == 1
    assert set(anchor_bundles[0].customer_ids) == {5, 7}
    assert tuple(bundle.customer_ids for bundle in unrelated_bundles) == ((10,), (7,))


def test_bundle_union_disjointness_and_external_exclusion() -> None:
    _, _, _, _, _, context, bundles = _adapt(
        operators.random_customer_removal,
        selected=[9, 11],
        count=2,
    )
    memberships = [set(bundle.customer_ids) for bundle in bundles]

    assert set.union(*memberships) == set(context.actually_unassigned_customer_ids)
    assert memberships[0].isdisjoint(memberships[1])
    assert all(
        membership.isdisjoint(context.external_boundary_entities.customer_ids)
        for membership in memberships
    )


def test_external_boundary_projection_is_preserved_by_real_omega_path() -> None:
    config, data, source, _, destroyed, context, _ = _adapt(
        operators.random_customer_removal,
        selected=[5],
    )
    removed = set(context.actually_unassigned_customer_ids)
    before = operators.external_boundary_business_projection(source, removed)
    repaired = operators.cascade_repair(
        destroyed, np.random.default_rng(29), data, config
    )

    assert repaired.metadata["cascade_repair_diagnostics"]["status"] == "success"
    assert operators.external_boundary_business_projection(repaired, removed) == before


def test_structural_cycle_is_a_controlled_failure() -> None:
    edges = (
        adapter.AtomicStructuralEdge("a", "test", 1, 2),
        adapter.AtomicStructuralEdge("b", "test", 2, 1),
    )

    with pytest.raises(adapter.OrdinaryCascadeAdapterError, match="cycle"):
        adapter._partition_and_order((1, 2), edges)


def test_bundle_ids_and_context_fingerprint_are_deterministic_three_runs() -> None:
    rows = []
    for _ in range(3):
        _, _, _, _, destroyed, context, bundles = _adapt(
            operators.random_customer_removal,
            selected=[5],
        )
        rows.append(
            (
                context.context_id,
                tuple(bundle.bundle_id for bundle in bundles),
                tuple(bundle.contract_fingerprint() for bundle in bundles),
                destroyed.cache_signature(),
            )
        )

    assert rows[0] == rows[1] == rows[2]


@pytest.mark.parametrize("failure_kind", ("stale", "invalid_source", "capability"))
def test_invalid_or_stale_context_fails_cleanly(failure_kind: str) -> None:
    config, data, source, _, destroyed, context, _ = _adapt(
        operators.random_customer_removal,
        selected=[10],
    )
    if failure_kind == "stale":
        destroyed.van_routes["van_0"].insert(1, 999)
    elif failure_kind == "invalid_source":
        destroyed.metadata[ACTIVE_REMOVAL_CONTEXT_KEY] = replace(
            context, source_destroy_operator="unsupported"
        )
    else:
        destroyed.metadata[ACTIVE_REMOVAL_CONTEXT_KEY] = replace(
            context, producer_capabilities=("spoofed",)
        )

    repaired = operators.cascade_repair(
        destroyed, np.random.default_rng(29), data, config
    )
    diagnostics = repaired.metadata["cascade_repair_diagnostics"]

    assert diagnostics["status"] == "failure"
    assert active_removal_context(repaired) is None
    assert active_removal_context(source) is None


def test_preinstalled_adapted_contract_without_context_is_rejected() -> None:
    config, data, source, _, destroyed, context, bundles = _adapt(
        operators.random_customer_removal,
        selected=[10],
    )
    detach_active_removal_context(destroyed)
    adapter.install_adapted_cascade_contract(destroyed, context, bundles)

    repaired = operators.cascade_repair(
        destroyed, np.random.default_rng(29), data, config
    )

    assert repaired.metadata["cascade_repair_diagnostics"]["status"] == "failure"
    assert "missing its active source context" in repaired.metadata[
        "cascade_repair_diagnostics"
    ]["reason"]
    assert active_removal_context(repaired) is None


def test_malformed_adapted_contract_is_controlled_by_validator() -> None:
    _, _, _, _, destroyed, context, bundles = _adapt(
        operators.random_customer_removal,
        selected=[10],
    )
    detach_active_removal_context(destroyed)
    adapter.install_adapted_cascade_contract(destroyed, context, bundles)
    destroyed.metadata["cascade_contract"]["actual_unassigned_customer_ids"] = (
        "not-an-int",
    )

    validated, errors = operators._validated_cascade_bundles(destroyed)

    assert validated is None
    assert any("malformed" in error for error in errors)


def test_native_cascade_bypasses_adapter_and_remains_exact(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("native Cascade path called ordinary adapter")

    monkeypatch.setattr(operators, "adapt_removal_context_to_cascade_bundles", forbidden)
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = np.random.default_rng(29)
    destroyed = operators.cascade_aware_removal(source, rng, data, config)
    native_contract = dict(destroyed.metadata["cascade_contract"])
    native_bundles = tuple(
        bundle.canonical_json() for bundle in destroyed.metadata["cascade_bundles"]
    )
    repaired = operators.cascade_repair(destroyed, rng, data, config)
    diagnostics = repaired.metadata["cascade_repair_diagnostics"]
    row = diagnostics["bundles"][0]
    stable_sequence = (
        row["bundle_id"],
        row["raw_bundle_strategy_count"],
        row["feasible_bundle_strategy_count"],
        row["unique_bundle_strategy_count"],
        row["strategy_generation_sequence"],
        row["selected_strategy_identity"],
        round(row["selected_objective"], 9),
    )

    assert native_contract["destroy_call_id"] == (
        "85e5862611154e12ca70c77ed253dd4c4e0b0ee5d825033781752b690e2e7176"
    )
    assert native_bundles
    assert "ordinary_adapter_call_count" not in diagnostics
    assert hashlib.sha256(repr(stable_sequence).encode()).hexdigest() == (
        "5723032f866258bfdca59723af105deca19f9880202acd8d20e8886e1b2ea010"
    )
    assert _business_fingerprint(repaired) == PAIR_BASELINE["Cascade+Cascade"][1]


@pytest.mark.parametrize(("name", "destroy"), ORDINARY_DESTROYS)
def test_new_pair_enters_real_omega_and_cleans_context(name, destroy, monkeypatch) -> None:
    calls = []
    original = operators._enumerate_bundle_reconstruction_strategies

    def recording(*args, **kwargs):
        calls.append(args[1].source_operator)
        return original(*args, **kwargs)

    monkeypatch.setattr(operators, "_enumerate_bundle_reconstruction_strategies", recording)
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = np.random.default_rng(29)
    destroyed = destroy(source, rng, data, config)
    repaired = operators.cascade_repair(destroyed, rng, data, config)
    diagnostics = repaired.metadata["cascade_repair_diagnostics"]

    assert calls == [destroy.__name__]
    assert diagnostics["ordinary_adapter_call_count"] == 1
    assert diagnostics["bundles"][0]["raw_bundle_strategy_count"] > 0
    assert diagnostics["status"] == "success"
    assert active_removal_context(source) is None
    assert active_removal_context(repaired) is None


@pytest.mark.parametrize(("name", "destroy"), ORDINARY_DESTROYS)
def test_new_pairs_never_call_other_repair_fallbacks(name, destroy, monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("repair fallback called")

    for repair_name in (
        "best_mode_repair",
        "greedy_van_repair",
        "greedy_drone_repair",
        "regret_repair",
    ):
        monkeypatch.setattr(operators, repair_name, forbidden)
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = np.random.default_rng(29)
    repaired = operators.cascade_repair(destroy(source, rng, data, config), rng, data, config)

    assert repaired.metadata["cascade_repair_diagnostics"]["status"] == "success"


def test_empty_omega_fails_atomically(monkeypatch) -> None:
    config, data, source, _, destroyed, context, _ = _adapt(
        operators.random_customer_removal,
        selected=[10],
    )
    destroyed_fingerprint = _business_fingerprint(destroyed)
    monkeypatch.setattr(
        operators,
        "_enumerate_bundle_reconstruction_strategies",
        lambda state, bundle, **kwargs: ([], _empty_row(bundle)),
    )
    repaired = operators.cascade_repair(
        destroyed, np.random.default_rng(29), data, config
    )

    assert repaired.metadata["cascade_repair_diagnostics"]["status"] == "failure"
    assert "empty feasible strategy set" in repaired.metadata[
        "cascade_repair_diagnostics"
    ]["reason"]
    assert _business_fingerprint(repaired) == destroyed_fingerprint
    assert active_removal_context(repaired) is None
    assert active_removal_context(source) is None


def test_second_bundle_failure_rolls_back_first(monkeypatch) -> None:
    config, data, source, _, destroyed, _, bundles = _adapt(
        operators.random_customer_removal,
        selected=[9, 11],
        count=2,
    )
    assert len(bundles) == 2
    destroyed_fingerprint = _business_fingerprint(destroyed)
    original = operators._enumerate_bundle_reconstruction_strategies
    calls = 0

    def fail_second(state, bundle, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return [], _empty_row(bundle)
        return original(state, bundle, **kwargs)

    monkeypatch.setattr(operators, "_enumerate_bundle_reconstruction_strategies", fail_second)
    repaired = operators.cascade_repair(
        destroyed, np.random.default_rng(29), data, config
    )

    assert calls == 2
    assert repaired.metadata["cascade_repair_diagnostics"]["status"] == "failure"
    assert _business_fingerprint(repaired) == destroyed_fingerprint


def test_adapter_is_lazy_only_for_the_three_new_pairs(monkeypatch) -> None:
    original = operators.adapt_removal_context_to_cascade_bundles
    calls = []

    def recording(context, state, **kwargs):
        calls.append(context.source_destroy_operator)
        return original(context, state, **kwargs)

    monkeypatch.setattr(operators, "adapt_removal_context_to_cascade_bundles", recording)
    destroys = (
        operators.random_customer_removal,
        operators.greedy_removal,
        operators.related_customer_removal,
        operators.cascade_aware_removal,
    )
    repairs = (
        operators.best_mode_repair,
        operators.greedy_van_repair,
        operators.regret_repair,
        operators.cascade_repair,
    )
    for destroy in destroys:
        for repair in repairs:
            config, data, source, _ = _coordinated_fixture()
            _set_destroy_count(config, data, 1)
            rng = np.random.default_rng(29)
            repair(destroy(source, rng, data, config), rng, data, config)

    assert calls == list(adapter.ORDINARY_CASCADE_SOURCES)


def test_existing_unrelated_repairs_have_identical_work_counts(monkeypatch) -> None:
    original_objective = operators.objective
    original_checker = operators.check_solution_feasible

    for repair_name in ("best_mode_repair", "greedy_van_repair", "regret_repair"):
        rows = []
        for direct_body in (False, True):
            counters = {"objective": 0, "checker": 0}

            def counting_objective(*args, **kwargs):
                counters["objective"] += 1
                return original_objective(*args, **kwargs)

            def counting_checker(*args, **kwargs):
                counters["checker"] += 1
                return original_checker(*args, **kwargs)

            monkeypatch.setattr(operators, "objective", counting_objective)
            monkeypatch.setattr(operators, "check_solution_feasible", counting_checker)
            config, data, source, _ = _coordinated_fixture()
            _set_destroy_count(config, data, 1)
            rng = np.random.default_rng(29)
            destroyed = operators.random_customer_removal(source, rng, data, config)
            repair = getattr(operators, repair_name)
            trace = []
            kwargs = (
                {"trace_collector": trace.append}
                if repair_name in {"greedy_van_repair", "regret_repair"}
                else {}
            )
            if direct_body:
                detach_active_removal_context(destroyed)
                repaired = repair.__wrapped__(destroyed, rng, data, config, **kwargs)
            else:
                repaired = repair(destroyed, rng, data, config, **kwargs)
            rows.append(
                (
                    counters.copy(),
                    _business_fingerprint(repaired),
                    _stable_diagnostic(trace),
                )
            )
        assert rows[0] == rows[1]


def test_existing_13_pair_baseline_and_16_pair_contract_matrix() -> None:
    destroys = (
        ("Random", operators.random_customer_removal),
        ("Greedy", operators.greedy_removal),
        ("Related", operators.related_customer_removal),
        ("Cascade", operators.cascade_aware_removal),
    )
    repairs = (
        ("Global", operators.best_mode_repair),
        ("Local", operators.greedy_van_repair),
        ("Regret", operators.regret_repair),
        ("Cascade", operators.cascade_repair),
    )
    categories = {"A": 0, "B": 0, "C": 0, "D": 0}
    existing = 0
    for destroy_name, destroy in destroys:
        for repair_name, repair in repairs:
            config, data, source, _ = _coordinated_fixture()
            _set_destroy_count(config, data, 1)
            rng = np.random.default_rng(29)
            pair_name = f"{destroy_name}+{repair_name}"
            trace = []
            try:
                destroyed = destroy(source, rng, data, config)
                kwargs = (
                    {"trace_collector": trace.append}
                    if repair_name in {"Local", "Regret"}
                    else {}
                )
                repaired = repair(destroyed, rng, data, config, **kwargs)
            except BaseException:
                categories["D"] += 1
                continue
            diagnostics = repaired.metadata.get("cascade_repair_diagnostics", {})
            reason = str(diagnostics.get("reason", ""))
            if "missing cascade contract" in reason or "rejected context" in reason:
                categories["C"] += 1
                continue
            feasible, _ = check_solution_feasible(repaired, data, config)
            if diagnostics.get("status") == "failure" or not feasible:
                categories["B"] += 1
            else:
                categories["A"] += 1

            if not (repair_name == "Cascade" and destroy_name != "Cascade"):
                existing += 1
                expected = PAIR_BASELINE[pair_name]
                cost, _ = objective(repaired, data, config)
                assert cost == pytest.approx(expected[0])
                assert _business_fingerprint(repaired) == expected[1]
                assert feasible is expected[2]
                if repair_name in {"Local", "Regret"}:
                    assert hashlib.sha256(
                        repr(_stable_diagnostic(trace)).encode()
                    ).hexdigest() == CANDIDATE_TRACE_BASELINE[pair_name]
            assert active_removal_context(source) is None
            assert active_removal_context(repaired) is None

    assert existing == 13
    assert categories["A"] + categories["B"] == 16
    assert categories["C"] == 0
    assert categories["D"] == 0


@pytest.mark.parametrize(("name", "destroy"), ORDINARY_DESTROYS)
def test_new_pair_is_deterministic_across_three_runs(name, destroy) -> None:
    rows = []
    for _ in range(3):
        config, data, source, _ = _coordinated_fixture()
        _set_destroy_count(config, data, 1)
        rng = np.random.default_rng(29)
        repaired = operators.cascade_repair(
            destroy(source, rng, data, config), rng, data, config
        )
        diagnostics = repaired.metadata["cascade_repair_diagnostics"]
        rows.append(
            (
                    _business_fingerprint(repaired),
                    _stable_without_timing(diagnostics),
                    repaired.unassigned,
            )
        )

    assert rows[0] == rows[1] == rows[2]
