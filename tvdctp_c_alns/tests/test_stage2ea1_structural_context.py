from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

import operators
from alns_solver import run_c_alns
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from objective import objective
from removal_structural_context import (
    ACTIVE_REMOVAL_CONTEXT_KEY,
    CASCADE_PRODUCER_CAPABILITIES,
    COMMON_PRODUCER_CAPABILITIES,
    RemovalContextContractError,
    active_removal_context,
    capture_structural_projection,
    discard_active_removal_context,
    removal_context_boundary,
    structural_business_fingerprint,
    validate_removal_structural_context,
)
from tests.test_stage2d0_cascade_contract import (
    FixedChoiceRng,
    _coordinated_fixture,
    _set_destroy_count,
)


PAPER_DESTROYS = (
    operators.random_customer_removal,
    operators.greedy_removal,
    operators.related_customer_removal,
    operators.cascade_aware_removal,
)


def _business_fingerprint(state) -> str:
    return hashlib.sha256(repr(state.cache_signature()).encode("utf-8")).hexdigest()


def _rng_digest(rng: np.random.Generator) -> str:
    payload = json.dumps(
        rng.bit_generator.state,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_diagnostic(value):
    if isinstance(value, dict):
        return tuple(
            (key, _stable_diagnostic(item))
            for key, item in sorted(value.items())
            if "seconds" not in key
        )
    if isinstance(value, list):
        return tuple(_stable_diagnostic(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_stable_diagnostic(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_stable_diagnostic(item) for item in value))
    return value


class ScalarChoiceRng:
    def __init__(self, selected: int) -> None:
        self.selected = int(selected)
        self.calls = []

    def choice(self, values, size=None, replace=True):
        self.calls.append((tuple(int(value) for value in values), size, bool(replace)))
        if size is None:
            return self.selected
        return np.asarray([self.selected], dtype=int)


def _legacy_random(state, rng, data, config):
    destroyed = state.copy()
    operators._clear_stale_cascade_metadata(destroyed)
    served = operators._served_customers(destroyed)
    count = min(operators._removal_count(data, config), len(served))
    selected = rng.choice(served, size=count, replace=False).tolist() if served else []
    operators._record_destroy_diagnostics(destroyed, selected, data)
    return operators._remove_customers(destroyed, selected)


def _legacy_greedy(state, rng, data, config):
    destroyed = state.copy()
    operators._clear_stale_cascade_metadata(destroyed)
    base_cost, _ = operators.objective(destroyed.copy(), data, config)
    scores = []
    for customer in operators._served_customers(destroyed):
        trial = destroyed.copy()
        operators._remove_customer(trial, customer)
        trial.clean_unassigned(customer)
        trial_cost, _ = operators.objective(trial, data, config)
        scores.append((base_cost - trial_cost, customer))
    count = min(operators._removal_count(data, config), len(scores))
    selected = [customer for _, customer in sorted(scores, reverse=True)[:count]]
    operators._record_destroy_diagnostics(destroyed, selected, data)
    return operators._remove_customers(destroyed, selected)


def _legacy_related(state, rng, data, config):
    destroyed = state.copy()
    operators._clear_stale_cascade_metadata(destroyed)
    served = operators._served_customers(destroyed)
    if not served:
        return destroyed
    seed = int(rng.choice(served))
    count = min(operators._removal_count(data, config), len(served))
    selected = sorted(
        served, key=lambda customer: data.ground_distance_matrix[seed, customer]
    )[:count]
    operators._record_destroy_diagnostics(destroyed, selected, data)
    return operators._remove_customers(destroyed, selected)


@pytest.mark.parametrize(
    ("current", "legacy", "expected_selected", "expected_output"),
    (
        (
            operators.random_customer_removal,
            _legacy_random,
            (12,),
            "994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978",
        ),
        (
            operators.greedy_removal,
            _legacy_greedy,
            (7,),
            "ade2fc27ba74b9753cd49b4f68f1ff6e08d9773140ae99c000c7d11a82f846eb",
        ),
        (
            operators.related_customer_removal,
            _legacy_related,
            (12,),
            "994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978",
        ),
    ),
)
def test_ordinary_destroy_strict_equivalence(
    current, legacy, expected_selected, expected_output
) -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    source_before = source.cache_signature()
    legacy_rng = np.random.default_rng(29)
    current_rng = np.random.default_rng(29)

    expected = legacy(source, legacy_rng, data, config)
    actual = current(source, current_rng, data, config)
    context = active_removal_context(actual)

    assert source.cache_signature() == source_before
    assert expected.cache_signature() == actual.cache_signature()
    assert _rng_digest(legacy_rng) == _rng_digest(current_rng)
    assert _business_fingerprint(actual) == expected_output
    assert context is not None
    assert context.selected_removed_customer_ids == expected_selected
    assert context.actually_unassigned_customer_ids == tuple(sorted(actual.unassigned))
    assert context.deletion_attempt_order == tuple(actual.unassigned)


def test_greedy_trial_sequence_and_ranking_are_unchanged(monkeypatch) -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    original_objective = operators.objective
    trace = []

    def recording_objective(state, data, config):
        value = original_objective(state, data, config)
        trace.append((state.cache_signature(), value[0]))
        return value

    monkeypatch.setattr(operators, "objective", recording_objective)
    _legacy_greedy(source, np.random.default_rng(29), data, config)
    legacy_trace = tuple(trace)
    trace.clear()
    actual = operators.greedy_removal(source, np.random.default_rng(29), data, config)

    assert tuple(trace) == legacy_trace
    assert active_removal_context(actual).selected_removed_customer_ids == (7,)


def test_related_seed_and_static_order_are_unchanged() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = np.random.default_rng(29)
    destroyed = operators.related_customer_removal(source, rng, data, config)
    context = active_removal_context(destroyed)
    ranking = sorted(
        operators._served_customers(source),
        key=lambda customer: data.ground_distance_matrix[12, customer],
    )

    assert ranking == [12, 9, 5, 6, 11, 8, 10, 7]
    assert context.customer_selection_order == (12,)
    assert context.selected_removed_customer_ids == (12,)


def test_cascade_destroy_and_old_contract_strict_equivalence() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = np.random.default_rng(29)
    destroyed = operators.cascade_aware_removal(source, rng, data, config)
    context = active_removal_context(destroyed)
    contract = destroyed.metadata["cascade_contract"]
    bundles = destroyed.metadata["cascade_bundles"]

    assert _business_fingerprint(destroyed) == (
        "994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978"
    )
    assert context.customer_selection_order == (12,)
    assert context.selected_removed_customer_ids == (12,)
    assert context.cascade_dependency_trace == ()
    assert context.cascade_native_partition_evidence == ((12,),)
    assert context.cascade_native_dependency_order == ((12,),)
    assert contract["destroy_call_id"] == (
        "85e5862611154e12ca70c77ed253dd4c4e0b0ee5d825033781752b690e2e7176"
    )
    assert bundles[0].contract_fingerprint() == (
        "8eb99601571e8554f1c68edeaaa34f67241af5172cc7ed7bc4f47c4d56c51d9c"
    )
    assert operators.cascade_metadata_is_current(destroyed)


def test_selected_ids_and_actual_unassigned_are_distinct_facts() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    anchor = ids["same_anchor"]

    random_result = operators.random_customer_removal(
        source, FixedChoiceRng([anchor]), data, config
    )
    related_result = operators.related_customer_removal(
        source, ScalarChoiceRng(anchor), data, config
    )
    cascade_result = operators.cascade_aware_removal(
        source, FixedChoiceRng([anchor]), data, config
    )
    greedy_result = operators.greedy_removal(
        source, np.random.default_rng(29), data, config
    )

    assert active_removal_context(random_result).selected_removed_customer_ids == (5,)
    assert active_removal_context(random_result).actually_unassigned_customer_ids == (5, 7)
    assert active_removal_context(related_result).selected_removed_customer_ids == (5,)
    assert active_removal_context(related_result).actually_unassigned_customer_ids == (5, 7)
    assert active_removal_context(cascade_result).customer_selection_order == (5,)
    assert active_removal_context(cascade_result).selected_removed_customer_ids == (5, 7)
    assert active_removal_context(cascade_result).actually_unassigned_customer_ids == (5, 7)
    assert active_removal_context(greedy_result).selected_removed_customer_ids == (7,)
    assert active_removal_context(greedy_result).actually_unassigned_customer_ids == (7,)


def test_mutation_footprint_covers_route_sortie_links_and_carrier_transfer() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)

    route_result = operators.random_customer_removal(
        source, FixedChoiceRng([ids["plain_van_customer"]]), data, config
    )
    route_context = active_removal_context(route_result)
    assert route_context.mutation_footprint.mutated_van_route_ids == ("van_0",)
    assert route_context.mutation_footprint.mutated_contiguous_route_intervals

    cross_result = operators.random_customer_removal(
        source, FixedChoiceRng([ids["cross_drone_customer"]]), data, config
    )
    cross_footprint = active_removal_context(cross_result).mutation_footprint
    assert cross_footprint.removed_or_replaced_sortie_ids
    assert len(cross_footprint.mutated_launch_recovery_link_ids) == 2
    assert cross_footprint.mutated_coordination_edge_ids
    assert any("carrier" in relation for relation in cross_footprint.mutated_carrier_relation_ids)


def test_multi_customer_sortie_uses_authoritative_collateral_diff() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    first = source.drone_sorties[0]
    first["customers"] = [ids["same_drone_customer"], ids["plain_van_customer"]]
    source.van_routes[ids["launch_van"]] = [
        node
        for node in source.van_routes[ids["launch_van"]]
        if node != ids["plain_van_customer"]
    ]
    source.sync_primary_van_route()
    source.service_mode[ids["plain_van_customer"]] = "drone"

    destroyed = operators.random_customer_removal(
        source, FixedChoiceRng([ids["same_drone_customer"]]), data, config
    )
    context = active_removal_context(destroyed)

    assert context.selected_removed_customer_ids == (ids["same_drone_customer"],)
    assert context.actually_unassigned_customer_ids == tuple(
        sorted((ids["same_drone_customer"], ids["plain_van_customer"]))
    )
    assert context.mutation_footprint.mutated_sortie_customer_sequences[0].pre_customer_ids == (
        ids["same_drone_customer"],
        ids["plain_van_customer"],
    )


def test_external_boundary_is_direct_and_not_whole_route() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.random_customer_removal(
        source, FixedChoiceRng([10]), data, config
    )
    context = active_removal_context(destroyed)

    assert context.actually_unassigned_customer_ids == (10,)
    assert context.external_boundary_entities.customer_ids == (9, 11)
    assert 5 not in context.external_boundary_entities.customer_ids
    assert 12 not in context.external_boundary_entities.customer_ids


@pytest.mark.parametrize("destroy", PAPER_DESTROYS)
def test_context_and_algorithm_rng_are_deterministic_across_three_runs(destroy) -> None:
    rows = []
    for _ in range(3):
        config, data, source, _ = _coordinated_fixture()
        _set_destroy_count(config, data, 1)
        rng = np.random.default_rng(29)
        result = destroy(source, rng, data, config)
        context = active_removal_context(result)
        rows.append(
            (
                context,
                context.context_id,
                context.mutation_footprint,
                result.cache_signature(),
                _rng_digest(rng),
            )
        )
    assert rows[0] == rows[1] == rows[2]


def test_context_id_distinguishes_different_destroy_result() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    first = operators.random_customer_removal(source, FixedChoiceRng([10]), data, config)
    second = operators.random_customer_removal(source, FixedChoiceRng([12]), data, config)
    assert active_removal_context(first).context_id != active_removal_context(second).context_id


def test_structural_fingerprint_cache_and_stage2d_fingerprint_ignore_context() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.random_customer_removal(
        source, np.random.default_rng(29), data, config
    )
    without = destroyed.copy()
    discard_active_removal_context(without)

    assert structural_business_fingerprint(capture_structural_projection(destroyed)) == (
        structural_business_fingerprint(capture_structural_projection(without))
    )
    assert destroyed.cache_signature() == without.cache_signature()
    assert operators._state_business_fingerprint(destroyed) == (
        operators._state_business_fingerprint(without)
    )


def test_state_copy_shares_only_fully_immutable_context() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.random_customer_removal(
        source, np.random.default_rng(29), data, config
    )
    copied = destroyed.copy()
    original_context = active_removal_context(destroyed)
    copied_context = active_removal_context(copied)

    assert original_context is copied_context
    with pytest.raises(FrozenInstanceError):
        copied_context.context_id = "changed"
    copied.van_routes["van_0"].append(999)
    assert 999 not in destroyed.van_routes["van_0"]
    assert not hasattr(original_context, "state")
    assert not hasattr(original_context, "live_route")


def test_context_schema_is_repair_agnostic_and_capabilities_are_trusted() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    ordinary = active_removal_context(
        operators.random_customer_removal(source, np.random.default_rng(29), data, config)
    )
    cascade = active_removal_context(
        operators.cascade_aware_removal(source, np.random.default_rng(29), data, config)
    )

    assert ordinary.producer_capabilities == COMMON_PRODUCER_CAPABILITIES
    assert cascade.producer_capabilities == (
        COMMON_PRODUCER_CAPABILITIES + CASCADE_PRODUCER_CAPABILITIES
    )
    for forbidden in (
        "repair_bundles",
        "dependency_order",
        "repair_strategy",
        "objective_value",
        "repair_candidate",
        "selected_repair",
        "top_k",
        "beam",
    ):
        assert not hasattr(ordinary, forbidden)
    with pytest.raises(RemovalContextContractError):
        validate_removal_structural_context(
            replace(ordinary, producer_capabilities=("invented",))
        )


@pytest.mark.parametrize(
    ("destroy", "repair"),
    (
        (operators.random_customer_removal, operators.best_mode_repair),
        (operators.random_customer_removal, operators.greedy_van_repair),
        (operators.random_customer_removal, operators.regret_repair),
        (operators.cascade_aware_removal, operators.cascade_repair),
    ),
)
def test_public_repair_lifecycle_consumes_context(destroy, repair) -> None:
    config, data, current, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    best = current.copy()
    rng = np.random.default_rng(29)
    destroyed = destroy(current, rng, data, config)
    assert active_removal_context(destroyed) is not None

    repaired = repair(destroyed, rng, data, config)

    assert active_removal_context(destroyed) is None
    assert active_removal_context(repaired) is None
    assert active_removal_context(current) is None
    assert active_removal_context(best) is None


def test_nested_registered_repair_and_failure_paths_do_not_leak_context() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.random_customer_removal(
        source, np.random.default_rng(29), data, config
    )
    repaired = operators.greedy_drone_repair(
        destroyed, np.random.default_rng(29), data, config
    )
    assert active_removal_context(repaired) is None

    failing_input = operators.random_customer_removal(
        source, np.random.default_rng(29), data, config
    )

    @removal_context_boundary
    def controlled_failure(state):
        raise RuntimeError("controlled")

    with pytest.raises(RuntimeError, match="controlled"):
        controlled_failure(failing_input)
    assert active_removal_context(failing_input) is None


def test_stale_raw_context_is_explicitly_discarded_on_new_working_copy() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    first = operators.random_customer_removal(
        source, FixedChoiceRng([12]), data, config
    )
    first_context = active_removal_context(first)
    second = operators.related_customer_removal(first, ScalarChoiceRng(10), data, config)
    second_context = active_removal_context(second)

    assert active_removal_context(first) is first_context
    assert second_context is not first_context
    assert second_context.context_id != first_context.context_id


def test_objective_checker_and_violations_are_context_isolated() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    with_context = operators.random_customer_removal(
        source, np.random.default_rng(29), data, config
    )
    without_context = with_context.copy()
    discard_active_removal_context(without_context)

    with_cost, with_breakdown = objective(with_context, data, config)
    without_cost, without_breakdown = objective(without_context, data, config)
    with_feasible, with_violations = check_solution_feasible(with_context, data, config)
    without_feasible, without_violations = check_solution_feasible(
        without_context, data, config
    )

    assert with_cost == without_cost
    assert with_breakdown == without_breakdown
    assert with_feasible == without_feasible
    assert with_violations == without_violations


PAIR_BASELINE = {
    "Random+Global": (40927.316361140, "819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76", False, "returned"),
    "Random+Local": (40927.316361140, "819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76", False, "returned"),
    "Random+Regret": (926.373751792, "3f8b9bc597f3be2a267ad88c5a6c2640e877eb395973824a7c40a204956ac7fc", True, "returned"),
    "Random+Cascade": (10926.095429883, "994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978", False, "failure"),
    "Greedy+Global": (765.252317540, "da4451935d067199fc880bbde649a891258dc027df8b833b3e8bbeaaf9217e76", True, "returned"),
    "Greedy+Local": (773.150287337, "95a1746970f9d4d18841f0261f05f6a4d1783c92923359249b2e1db510aeb933", True, "returned"),
    "Greedy+Regret": (765.252317540, "da4451935d067199fc880bbde649a891258dc027df8b833b3e8bbeaaf9217e76", True, "returned"),
    "Greedy+Cascade": (10762.799812194, "ade2fc27ba74b9753cd49b4f68f1ff6e08d9773140ae99c000c7d11a82f846eb", False, "failure"),
    "Related+Global": (40927.316361140, "819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76", False, "returned"),
    "Related+Local": (40927.316361140, "819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76", False, "returned"),
    "Related+Regret": (926.373751792, "3f8b9bc597f3be2a267ad88c5a6c2640e877eb395973824a7c40a204956ac7fc", True, "returned"),
    "Related+Cascade": (10926.095429883, "994ee663d6eab6c29ae1fe15c05c872811903b8c57b8de5826a3cfe3437c0978", False, "failure"),
    "Cascade+Global": (40927.316361140, "819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76", False, "returned"),
    "Cascade+Local": (40927.316361140, "819471d0e0d8b6a5e0919c5d2b98dc6000308979b41703d6a2df4fb600ad9a76", False, "returned"),
    "Cascade+Regret": (926.373751792, "3f8b9bc597f3be2a267ad88c5a6c2640e877eb395973824a7c40a204956ac7fc", True, "returned"),
    "Cascade+Cascade": (927.880274816, "56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e", True, "success"),
}

CANDIDATE_TRACE_BASELINE = {
    "Random+Local": "1ec78cd24b2d10f4736eb8f85c9fc9edd4d55b8b4f64e9e1afbc5068155bc943",
    "Random+Regret": "b4b209050fc7fea02d550e14e0c0d39b1827a9bd03f4c754168e64d7961a7b65",
    "Greedy+Local": "d023cf038d2c5cfcebb09f30a18ee16a7f5188478bbae33833368832761ea74f",
    "Greedy+Regret": "1b8736acc5cf5a18cc4290b707a063626fa914f861eeeaabe12baba84e68626d",
    "Related+Local": "1ec78cd24b2d10f4736eb8f85c9fc9edd4d55b8b4f64e9e1afbc5068155bc943",
    "Related+Regret": "b4b209050fc7fea02d550e14e0c0d39b1827a9bd03f4c754168e64d7961a7b65",
    "Cascade+Local": "1ec78cd24b2d10f4736eb8f85c9fc9edd4d55b8b4f64e9e1afbc5068155bc943",
    "Cascade+Regret": "b4b209050fc7fea02d550e14e0c0d39b1827a9bd03f4c754168e64d7961a7b65",
}


def test_existing_13_pairs_and_three_blocked_pairs_are_exactly_unchanged() -> None:
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
    compatible = 0
    incompatible = 0
    for destroy_name, destroy in destroys:
        for repair_name, repair in repairs:
            config, data, source, _ = _coordinated_fixture()
            _set_destroy_count(config, data, 1)
            rng = np.random.default_rng(29)
            destroyed = destroy(source, rng, data, config)
            pair_name = f"{destroy_name}+{repair_name}"
            trace = []
            if repair_name in {"Local", "Regret"}:
                repaired = repair(
                    destroyed,
                    rng,
                    data,
                    config,
                    trace_collector=trace.append,
                )
                assert hashlib.sha256(
                    repr(_stable_diagnostic(trace)).encode()
                ).hexdigest() == CANDIDATE_TRACE_BASELINE[pair_name]
            else:
                repaired = repair(destroyed, rng, data, config)
            cost, _ = objective(repaired, data, config)
            feasible, _ = check_solution_feasible(repaired, data, config)
            status = repaired.metadata.get("cascade_repair_diagnostics", {}).get(
                "status", "returned"
            )
            expected = PAIR_BASELINE[pair_name]
            assert cost == pytest.approx(expected[0])
            assert _business_fingerprint(repaired) == expected[1]
            assert feasible is expected[2]
            assert status == expected[3]
            if repair_name == "Cascade" and destroy_name != "Cascade":
                incompatible += 1
                assert "missing cascade contract" in repaired.metadata[
                    "cascade_repair_diagnostics"
                ]["reason"]
            else:
                compatible += 1
            assert active_removal_context(repaired) is None
    assert (compatible, incompatible) == (13, 3)


def test_cascade_plus_cascade_candidate_sequence_and_contract_are_exact() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = np.random.default_rng(29)
    destroyed = operators.cascade_aware_removal(source, rng, data, config)
    contract = dict(destroyed.metadata["cascade_contract"])
    bundles = tuple(bundle.canonical_json() for bundle in destroyed.metadata["cascade_bundles"])
    repaired = operators.cascade_repair(destroyed, rng, data, config)
    diagnostics = repaired.metadata["cascade_repair_diagnostics"]

    assert contract["source_operator"] == operators.CASCADE_SOURCE_OPERATOR
    assert bundles
    assert diagnostics["status"] == "success"
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
    assert hashlib.sha256(repr(stable_sequence).encode()).hexdigest() == (
        "5723032f866258bfdca59723af105deca19f9880202acd8d20e8886e1b2ea010"
    )
    assert _business_fingerprint(repaired) == PAIR_BASELINE["Cascade+Cascade"][1]


def test_solver_persistent_states_are_context_free() -> None:
    config = build_config(
        num_customers=4,
        num_orders=4,
        num_transshipments=2,
        num_containers=1,
        iterations=2,
        seed=42,
        drone_enabled=False,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    result = run_c_alns(data, config)

    assert active_removal_context(result.initial_state) is None
    assert active_removal_context(result.current_state) is None
    assert active_removal_context(result.best_state) is None
    assert ACTIVE_REMOVAL_CONTEXT_KEY not in result.history[-1]
