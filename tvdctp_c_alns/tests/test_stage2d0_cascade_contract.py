from __future__ import annotations

from dataclasses import replace
from typing import Sequence

import numpy as np
import pytest

import operators
from config import build_config
from dataset_loader import generate_toy_data
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from objective import objective
from state import CascadeBundleSnapshot


class RecordingRng:
    def __init__(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)
        self.calls: list[tuple[str, tuple[int, ...], int, bool]] = []

    def choice(self, values, size=None, replace=True):
        normalized = tuple(int(value) for value in values)
        self.calls.append(("choice", normalized, int(size), bool(replace)))
        return self._rng.choice(values, size=size, replace=replace)


class FixedChoiceRng:
    def __init__(self, selected: Sequence[int]) -> None:
        self.selected = tuple(int(customer) for customer in selected)
        self.calls: list[tuple[tuple[int, ...], int, bool]] = []

    def choice(self, values, size=None, replace=True):
        normalized = tuple(int(value) for value in values)
        count = int(size)
        self.calls.append((normalized, count, bool(replace)))
        assert set(self.selected).issubset(normalized)
        assert len(self.selected) == count
        return np.asarray(self.selected, dtype=int)


def _coordinated_fixture():
    config = build_config(
        num_customers=8,
        num_orders=8,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={3: 2, 4: 2},
        drones_per_van=2,
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    data.drone_eligible = {customer: True for customer in data.customers}
    for customer in data.customers:
        data.demands[customer] = 1.0
        data.pickup_demands[customer] = 0.0
        data.service_times[customer] = 0.0
        data.time_windows[customer] = (0.0, 10_000.0)

    state = initial_solution(data, config)
    selected = int(state.selected_transshipment)
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == selected
    ]
    launch_van, recovery_van = selected_vans[:2]
    launch_drones = [
        drone_id
        for drone_id, carrier in sorted(state.drone_initial_carrier.items())
        if carrier == launch_van
    ]
    same_drone_id, cross_drone_id = launch_drones[:2]
    (
        same_anchor,
        recovery_anchor,
        same_drone_customer,
        cross_drone_customer,
        plain_van_customer,
        *other_van_customers,
    ) = data.customers

    state.van_routes = {
        launch_van: [
            selected,
            same_anchor,
            plain_van_customer,
            *other_van_customers,
            selected,
        ],
        recovery_van: [selected, recovery_anchor, selected],
    }
    state.sync_primary_van_route()
    state.drone_sorties = [
        {
            "drone_id": same_drone_id,
            "launch_van_id": launch_van,
            "recovery_van_id": launch_van,
            "launch": same_anchor,
            "customers": [same_drone_customer],
            "recovery": same_anchor,
            "launch_position": 1,
            "recovery_position": 1,
            "same_node": True,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
        },
        {
            "drone_id": cross_drone_id,
            "launch_van_id": launch_van,
            "recovery_van_id": recovery_van,
            "launch": selected,
            "customers": [cross_drone_customer],
            "recovery": recovery_anchor,
            "launch_position": 0,
            "recovery_position": 1,
            "same_node": False,
            "launch_time": 0.0,
            "recovery_time": 0.0,
            "van_waiting_time": 0.0,
            "drone_waiting_time": 0.0,
        },
    ]
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[same_drone_customer] = "drone"
    state.service_mode[cross_drone_customer] = "drone"
    state.unassigned = []

    ids = {
        "launch_van": launch_van,
        "recovery_van": recovery_van,
        "same_drone_id": same_drone_id,
        "cross_drone_id": cross_drone_id,
        "same_anchor": same_anchor,
        "recovery_anchor": recovery_anchor,
        "same_drone_customer": same_drone_customer,
        "cross_drone_customer": cross_drone_customer,
        "plain_van_customer": plain_van_customer,
    }
    return config, data, state, ids


def _set_destroy_count(config, data, count: int) -> None:
    config.alns.customer_removal_ratio = count / len(data.customers)


def _bundle_for_customer(state, customer: int) -> CascadeBundleSnapshot:
    return next(
        bundle
        for bundle in state.metadata["cascade_bundles"]
        if customer in bundle.customer_ids
    )


def _legacy_cascade_removal(state, rng, data, config):
    """Exact pre-Stage-2D.0 algorithm, retained as an equivalence oracle."""

    destroyed = state.copy()
    served = operators._served_customers(destroyed)
    count = min(operators._removal_count(data, config), len(served))
    initial = rng.choice(served, size=count, replace=False).tolist() if served else []
    removal = set(initial)

    changed = True
    while changed:
        changed = False
        for customer in list(removal):
            deps = operators._cascade_dependencies(destroyed, customer)
            if not deps.issubset(removal):
                removal |= deps
                changed = True

    bundles = []
    assigned = set()
    for sortie in destroyed.drone_sorties:
        launch, drone_customers, recovery = operators.sortie_nodes(sortie)
        related = set(drone_customers)
        if launch in data.customers:
            related.add(launch)
        if recovery in data.customers:
            related.add(recovery)
        bundle = sorted(related & removal)
        if bundle:
            bundles.append(bundle)
            assigned.update(bundle)
    for customer in sorted(removal - assigned):
        bundles.append([customer])

    destroyed = operators._remove_customers(destroyed, removal)
    operators._remove_duplicate_unassigned(destroyed)
    destroyed.metadata["cascade_removed"] = sorted(removal)
    destroyed.metadata["cascade_bundles"] = bundles
    return destroyed


def _bundle_customer_lists(state) -> list[list[int]]:
    return [list(bundle.customer_ids) for bundle in state.metadata["cascade_bundles"]]


def _business_projection(state) -> tuple[object, ...]:
    return state.cache_signature()


def test_snapshot_is_captured_from_pre_removal_state() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    before = source.copy()

    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )
    bundle = _bundle_for_customer(destroyed, ids["cross_drone_customer"])
    service = next(
        item
        for item in bundle.customer_service_snapshots
        if item.customer_id == ids["cross_drone_customer"]
    )
    subroute = bundle.removed_drone_subroutes[0]
    link = bundle.launch_recovery_snapshots[0]
    carrier = bundle.carrier_transfer_snapshots[0]

    assert bundle.captured_before_removal is True
    assert service.service_mode == before.service_mode[ids["cross_drone_customer"]]
    assert subroute.customer_ids == (ids["cross_drone_customer"],)
    assert subroute.launch_node == before.drone_sorties[1]["launch"]
    assert subroute.recovery_node == before.drone_sorties[1]["recovery"]
    assert link.launch_position == before.drone_sorties[1]["launch_position"]
    assert link.recovery_position == before.drone_sorties[1]["recovery_position"]
    assert carrier.initial_carrier_van_id == before.drone_initial_carrier[
        ids["cross_drone_id"]
    ]
    assert ids["cross_drone_customer"] not in destroyed.get_drone_customers()


def test_removal_business_result_and_rng_calls_match_legacy_algorithm() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    old_rng = RecordingRng(17)
    new_rng = RecordingRng(17)

    legacy = _legacy_cascade_removal(source, old_rng, data, config)
    current = operators.cascade_aware_removal(source, new_rng, data, config)

    assert current.metadata["cascade_removed"] == legacy.metadata["cascade_removed"]
    assert _bundle_customer_lists(current) == legacy.metadata["cascade_bundles"]
    assert [list(bundle.dependency_order) for bundle in current.metadata["cascade_bundles"]] == (
        legacy.metadata["cascade_bundles"]
    )
    assert _business_projection(current) == _business_projection(legacy)
    assert current.van_routes == legacy.van_routes
    assert current.drone_sorties == legacy.drone_sorties
    assert current.unassigned == legacy.unassigned
    assert current.service_mode == legacy.service_mode
    assert old_rng.calls == new_rng.calls

    old_cost, _ = objective(legacy.copy(), data, config)
    new_cost, _ = objective(current.copy(), data, config)
    assert new_cost == pytest.approx(old_cost)


def test_van_customer_snapshot_preserves_route_position_and_warehouse_context() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["plain_van_customer"]]),
        data,
        config,
    )
    bundle = _bundle_for_customer(destroyed, ids["plain_van_customer"])
    service = bundle.customer_service_snapshots[0]
    position = service.van_route_positions[0]
    route_snapshot = next(
        item for item in bundle.affected_route_segments if item.van_id == position.van_id
    )

    assert service.service_mode == "van"
    assert position.van_id == ids["launch_van"]
    assert source.van_routes[position.van_id][position.route_position] == (
        ids["plain_van_customer"]
    )
    assert position.warehouse_id == source.van_home[position.van_id]
    assert service.container_id == source.order_assignment[ids["plain_van_customer"]][
        "container_id"
    ]
    assert service.assigned_transshipment == source.order_assignment[
        ids["plain_van_customer"]
    ]["assigned_transshipment"]
    original_slice = source.van_routes[position.van_id][
        route_snapshot.start_position : route_snapshot.end_position + 1
    ]
    assert route_snapshot.route_nodes == tuple(original_slice)


def test_same_van_drone_snapshot_preserves_launch_recovery_and_carrier() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["same_drone_customer"]]),
        data,
        config,
    )
    bundle = _bundle_for_customer(destroyed, ids["same_drone_customer"])
    subroute = bundle.removed_drone_subroutes[0]
    link = bundle.launch_recovery_snapshots[0]
    carrier = bundle.carrier_transfer_snapshots[0]

    assert subroute.drone_id == ids["same_drone_id"]
    assert link.launch_van_id == ids["launch_van"]
    assert link.recovery_van_id == ids["launch_van"]
    assert link.same_van_recovery is True
    assert link.launch_node == ids["same_anchor"]
    assert link.recovery_node == ids["same_anchor"]
    assert carrier.launch_carrier_van_id == ids["launch_van"]
    assert carrier.recovery_carrier_van_id == ids["launch_van"]
    assert carrier.carrier_transfer is False


def test_cross_van_drone_snapshot_preserves_physical_transfer() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )
    bundle = _bundle_for_customer(destroyed, ids["cross_drone_customer"])
    link = bundle.launch_recovery_snapshots[0]
    carrier = bundle.carrier_transfer_snapshots[0]

    assert link.launch_van_id == ids["launch_van"]
    assert link.recovery_van_id == ids["recovery_van"]
    assert link.launch_position == 0
    assert link.recovery_position == 1
    assert link.same_van_recovery is False
    assert carrier.initial_carrier_van_id == ids["launch_van"]
    assert carrier.launch_carrier_van_id == ids["launch_van"]
    assert carrier.recovery_carrier_van_id == ids["recovery_van"]
    assert carrier.carrier_transfer is True
    assert len(bundle.affected_route_segments) == 2


def test_multiple_bundles_have_independent_ids_and_structural_snapshots() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng(
            [ids["same_drone_customer"], ids["cross_drone_customer"]]
        ),
        data,
        config,
    )
    same_bundle = _bundle_for_customer(destroyed, ids["same_drone_customer"])
    cross_bundle = _bundle_for_customer(destroyed, ids["cross_drone_customer"])

    assert same_bundle.bundle_id != cross_bundle.bundle_id
    assert set(same_bundle.customer_ids).isdisjoint(cross_bundle.customer_ids)
    assert {item.sortie_id for item in same_bundle.removed_drone_subroutes} == {
        "sortie:0"
    }
    assert {item.sortie_id for item in cross_bundle.removed_drone_subroutes} == {
        "sortie:1"
    }
    assert same_bundle.contract_fingerprint() != cross_bundle.contract_fingerprint()


@pytest.mark.parametrize(
    "destroy_operator",
    [
        operators.random_customer_removal,
        operators.greedy_removal,
        operators.related_customer_removal,
        operators.route_segment_removal,
        operators.drone_task_removal,
        operators.switch_transshipment_operator,
    ],
)
def test_non_cascade_destroy_clears_stale_cascade_metadata(destroy_operator) -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    cascade_destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )
    assert operators.cascade_metadata_is_current(cascade_destroyed)

    next_destroyed = destroy_operator(
        cascade_destroyed,
        np.random.default_rng(31),
        data,
        config,
    )

    assert all(key not in next_destroyed.metadata for key in operators.CASCADE_METADATA_KEYS)
    assert operators.cascade_metadata_is_current(next_destroyed) is False


def test_consecutive_cascade_destroys_replace_contract_and_use_new_source() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    first = operators.cascade_aware_removal(
        source, np.random.default_rng(11), data, config
    )
    first_call_id = first.metadata["cascade_contract"]["destroy_call_id"]
    first_bundle_ids = {
        bundle.bundle_id for bundle in first.metadata["cascade_bundles"]
    }

    second_source_fingerprint = operators._state_business_fingerprint(first)
    second = operators.cascade_aware_removal(
        first, np.random.default_rng(12), data, config
    )
    second_contract = second.metadata["cascade_contract"]
    second_bundle_ids = {
        bundle.bundle_id for bundle in second.metadata["cascade_bundles"]
    }

    assert second_contract["destroy_call_id"] != first_call_id
    assert second_contract["source_state_fingerprint"] == second_source_fingerprint
    assert first_bundle_ids.isdisjoint(second_bundle_ids)
    assert operators.cascade_metadata_is_current(second)
    for bundle in second.metadata["cascade_bundles"]:
        for service in bundle.customer_service_snapshots:
            assert service.service_mode == first.service_mode[service.customer_id]


def test_state_copy_isolates_cascade_metadata_and_snapshot_replacement() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )
    copied = destroyed.copy()
    original_bundle = destroyed.metadata["cascade_bundles"][0]
    replacement = replace(original_bundle, bundle_id="copy-only-bundle")
    copied.metadata["cascade_bundles"][0] = replacement
    copied.metadata["cascade_contract"]["bundle_ids"] = ("copy-only-bundle",)

    assert destroyed.metadata["cascade_bundles"][0] is not replacement
    assert destroyed.metadata["cascade_bundles"][0].bundle_id == original_bundle.bundle_id
    assert destroyed.metadata["cascade_contract"]["bundle_ids"] != (
        "copy-only-bundle",
    )
    assert operators.cascade_metadata_is_current(destroyed)
    assert operators.cascade_metadata_is_current(copied) is False


def test_fixed_seed_contract_is_deterministic_across_three_runs() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    results = [
        operators.cascade_aware_removal(
            source, np.random.default_rng(29), data, config
        )
        for _ in range(3)
    ]

    projections = [
        (
            result.metadata["cascade_removed"],
            tuple(bundle.customer_ids for bundle in result.metadata["cascade_bundles"]),
            tuple(bundle.dependency_order for bundle in result.metadata["cascade_bundles"]),
            tuple(bundle.bundle_id for bundle in result.metadata["cascade_bundles"]),
            tuple(bundle.canonical_json() for bundle in result.metadata["cascade_bundles"]),
            tuple(
                bundle.contract_fingerprint()
                for bundle in result.metadata["cascade_bundles"]
            ),
            result.metadata["cascade_contract"],
        )
        for result in results
    ]

    assert projections[0] == projections[1] == projections[2]
    assert all(operators.cascade_metadata_is_current(result) for result in results)


def test_identical_bundle_snapshot_has_identical_serialization_and_fingerprint() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    first = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["same_drone_customer"]]),
        data,
        config,
    ).metadata["cascade_bundles"][0]
    second = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["same_drone_customer"]]),
        data,
        config,
    ).metadata["cascade_bundles"][0]

    assert first == second
    assert first.customer_ids == first.dependency_order
    assert first.dependency_order_semantics == (
        "current implementation order; Paper unspecified"
    )
    assert first.canonical_json() == second.canonical_json()
    assert first.contract_fingerprint() == second.contract_fingerprint()


def test_metadata_does_not_change_checker_objective_or_business_fingerprint() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )
    stripped = destroyed.copy()
    operators._clear_stale_cascade_metadata(stripped)

    with_metadata_result = check_solution_feasible(destroyed.copy(), data, config)
    without_metadata_result = check_solution_feasible(stripped.copy(), data, config)
    with_metadata_cost, _ = objective(destroyed.copy(), data, config)
    without_metadata_cost, _ = objective(stripped.copy(), data, config)

    assert with_metadata_result == without_metadata_result
    assert with_metadata_cost == pytest.approx(without_metadata_cost)
    assert _business_projection(destroyed) == _business_projection(stripped)


def test_contract_validator_rejects_business_state_mutation() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["plain_van_customer"]]),
        data,
        config,
    )
    assert operators.cascade_metadata_is_current(destroyed)

    extra_customer = next(
        customer for customer in data.customers if customer not in destroyed.unassigned
    )
    destroyed.unassigned.append(extra_customer)

    assert operators.cascade_metadata_is_current(destroyed) is False
