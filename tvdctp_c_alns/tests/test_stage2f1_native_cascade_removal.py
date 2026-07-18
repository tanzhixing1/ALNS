from __future__ import annotations

from collections import Counter

import pytest

import operators
from feasibility import check_solution_feasible
from removal_structural_context import (
    RemovalContextContractError,
    active_removal_context,
    capture_structural_projection,
)
from tests.test_stage2d0_cascade_contract import (
    FixedChoiceRng,
    RecordingRng,
    _coordinated_fixture,
    _set_destroy_count,
)


def _graph(source, data):
    return operators._build_native_cascade_customer_dependency_graph(
        capture_structural_projection(source), data.customers
    )


def _edges(graph, predicate_id: str):
    return [edge for edge in graph.edges if edge.predicate_id == predicate_id]


def _edge(
    source: int,
    target: int,
    rank: int,
    *,
    predicate: str = "TEST",
    provenance: str | None = None,
):
    return operators.NativeCascadeDependencyEdge(
        predicate_id=predicate,
        source_customer=source,
        target_customer=target,
        structural_rank=(rank, rank, rank, rank),
        provenance=provenance or f"edge:{source}->{target}:{rank}",
    )


def _manual_graph(customer_ids, edges):
    return operators.NativeCascadeDependencyGraph(
        customer_ids=tuple(customer_ids),
        edges=tuple(
            sorted(
                edges,
                key=lambda edge: (
                    edge.source_customer,
                    *edge.stable_identity(),
                ),
            )
        ),
    )


def test_same_subroute_predicate_extracts_customers_and_symmetric_edges() -> None:
    _, data, source, ids = _coordinated_fixture()
    graph = _graph(source, data)
    pairs = {
        (edge.source_customer, edge.target_customer)
        for edge in _edges(graph, "NCD-A-SAME-SUBROUTE")
    }

    assert (ids["same_anchor"], ids["same_drone_customer"]) in pairs
    assert (ids["same_drone_customer"], ids["same_anchor"]) in pairs
    assert (ids["recovery_anchor"], ids["cross_drone_customer"]) in pairs
    assert (ids["cross_drone_customer"], ids["recovery_anchor"]) in pairs


def test_same_subroute_predicate_excludes_unrelated_customer() -> None:
    _, data, source, ids = _coordinated_fixture()
    graph = _graph(source, data)

    assert graph.outgoing(ids["plain_van_customer"]) == ()
    assert all(
        ids["plain_van_customer"]
        not in (edge.source_customer, edge.target_customer)
        for edge in graph.edges
    )


def test_same_subroute_predicate_excludes_non_customer_anchors_and_deduplicates_occurrences() -> None:
    _, data, source, ids = _coordinated_fixture()
    graph = _graph(source, data)
    customer_set = set(data.customers)
    cross_edges = [
        edge
        for edge in _edges(graph, "NCD-A-SAME-SUBROUTE")
        if ids["cross_drone_customer"]
        in (edge.source_customer, edge.target_customer)
    ]

    assert int(source.selected_transshipment) not in graph.customer_ids
    assert all(
        edge.source_customer in customer_set and edge.target_customer in customer_set
        for edge in graph.edges
    )
    assert Counter(
        (edge.predicate_id, edge.source_customer, edge.target_customer)
        for edge in graph.edges
    ).most_common(1)[0][1] == 1
    assert {
        (edge.source_customer, edge.target_customer) for edge in cross_edges
    } == {
        (ids["recovery_anchor"], ids["cross_drone_customer"]),
        (ids["cross_drone_customer"], ids["recovery_anchor"]),
    }


def test_launch_recovery_predicate_preserves_direction_rank_and_provenance() -> None:
    _, data, source, ids = _coordinated_fixture()
    graph = _graph(source, data)
    directed = _edges(graph, "NCD-B-LAUNCH-RECOVERY")

    assert len(directed) == 1
    edge = directed[0]
    assert (edge.source_customer, edge.target_customer) == (
        ids["same_anchor"],
        ids["same_anchor"],
    )
    assert edge.structural_rank == (0, 0, 0, 1)
    assert edge.provenance.endswith(":launch-recovery-order")


def test_launch_recovery_predicate_does_not_reverse_directed_edge() -> None:
    _, data, source, ids = _coordinated_fixture()
    source.drone_sorties[0]["recovery"] = ids["recovery_anchor"]
    source.drone_sorties[0]["recovery_van_id"] = ids["recovery_van"]
    source.drone_sorties[0]["recovery_position"] = 1
    source.drone_sorties[0]["same_node"] = False
    graph = _graph(source, data)
    directed_pairs = {
        (edge.source_customer, edge.target_customer)
        for edge in _edges(graph, "NCD-B-LAUNCH-RECOVERY")
    }

    assert (ids["same_anchor"], ids["recovery_anchor"]) in directed_pairs
    assert (ids["recovery_anchor"], ids["same_anchor"]) not in directed_pairs


def test_launch_recovery_predicate_requires_two_customer_endpoints() -> None:
    _, data, source, ids = _coordinated_fixture()
    graph = _graph(source, data)
    cross_sortie_id = capture_structural_projection(source).drone_sortie_facts[1].sortie_id

    assert all(
        edge.provenance != f"{cross_sortie_id}:launch-recovery-order"
        for edge in _edges(graph, "NCD-B-LAUNCH-RECOVERY")
    )
    assert int(source.selected_transshipment) not in graph.customer_ids
    assert ids["recovery_anchor"] in graph.customer_ids


def test_non_customer_coordination_edges_do_not_enter_customer_graph() -> None:
    _, data, source, _ = _coordinated_fixture()
    projection = capture_structural_projection(source)
    graph = operators._build_native_cascade_customer_dependency_graph(
        projection, data.customers
    )

    assert any(
        fact.edge_kind in {"van-drone-launch", "van-drone-recovery"}
        for fact in projection.coordination_edge_facts
    )
    assert any(fact.transferred for fact in projection.carrier_transfer_facts)
    assert {edge.predicate_id for edge in graph.edges} <= {
        "NCD-A-SAME-SUBROUTE",
        "NCD-B-LAUNCH-RECOVERY",
    }


def test_multiple_occurrence_rank_uses_minimum_pre_destroy_sortie_rank() -> None:
    config, data, source, ids = _coordinated_fixture()
    launch_route = source.van_routes[ids["launch_van"]]
    launch_position = launch_route.index(ids["same_anchor"])
    launch_route.insert(launch_position + 1, ids["recovery_anchor"])
    source.van_routes[ids["recovery_van"]] = [
        node
        for node in source.van_routes[ids["recovery_van"]]
        if node != ids["recovery_anchor"]
    ]
    source.sync_primary_van_route()
    for index, sortie in enumerate(source.drone_sorties):
        sortie["launch"] = ids["same_anchor"]
        sortie["recovery"] = ids["recovery_anchor"]
        sortie["launch_van_id"] = ids["launch_van"]
        sortie["recovery_van_id"] = ids["launch_van"]
        sortie["launch_position"] = launch_position
        sortie["recovery_position"] = launch_position + 1
        sortie["same_node"] = False
        customer = int(sortie["customers"][0])
        data.drone_distance_matrix[ids["same_anchor"], customer] = 1.0
        data.drone_distance_matrix[customer, ids["recovery_anchor"]] = 1.0
    feasible, violations = check_solution_feasible(source.copy(), data, config)
    assert feasible is True, violations

    graph = _graph(source, data)
    repeated_a = next(
        edge
        for edge in _edges(graph, "NCD-A-SAME-SUBROUTE")
        if (edge.source_customer, edge.target_customer)
        == (ids["same_anchor"], ids["recovery_anchor"])
    )
    repeated_b = next(
        edge
        for edge in _edges(graph, "NCD-B-LAUNCH-RECOVERY")
        if (edge.source_customer, edge.target_customer)
        == (ids["same_anchor"], ids["recovery_anchor"])
    )

    assert repeated_a.structural_rank[0] == 0
    assert repeated_b.structural_rank[0] == 0
    first_sortie_id = capture_structural_projection(source).drone_sortie_facts[0].sortie_id
    assert repeated_a.provenance.startswith(first_sortie_id)
    assert repeated_b.provenance.startswith(first_sortie_id)


def test_ordered_closure_handles_one_hop_multi_hop_cycle_self_loop_and_duplicates() -> None:
    graph = _manual_graph(
        (1, 2, 3, 4),
        (
            _edge(1, 2, 0),
            _edge(1, 2, 1, provenance="duplicate"),
            _edge(2, 3, 0),
            _edge(3, 1, 0),
            _edge(3, 3, 1),
        ),
    )

    membership, order, trace = operators._native_cascade_fixed_point_closure(
        graph, (1,)
    )

    assert membership == {1, 2, 3}
    assert order == [1, 2, 3]
    assert trace == [(1, 2), (2, 3)]


def test_ordered_closure_handles_multi_source_merge_multiple_chains_and_isolated_seed() -> None:
    graph = _manual_graph(
        (1, 2, 3, 4, 5, 6, 7),
        (
            _edge(1, 3, 1),
            _edge(1, 2, 0),
            _edge(2, 5, 0),
            _edge(3, 5, 0),
            _edge(4, 6, 0),
        ),
    )

    membership, order, trace = operators._native_cascade_fixed_point_closure(
        graph, (4, 1, 7)
    )

    assert membership == {1, 2, 3, 4, 5, 6, 7}
    assert order == [4, 1, 7, 6, 2, 3, 5]
    assert trace == [(4, 6), (1, 2), (1, 3), (2, 5)]


def test_weak_component_partition_uses_directionless_connectivity_and_stable_order() -> None:
    graph = _manual_graph(
        (1, 2, 3, 4, 5),
        (
            _edge(2, 1, 0),
            _edge(2, 3, 1),
            _edge(4, 5, 0),
        ),
    )
    membership = {1, 2, 3, 4, 5}

    bundles = operators._native_cascade_weak_components(
        graph, membership, (3, 5, 1, 2, 4)
    )

    assert bundles == [[1, 2, 3], [4, 5]]
    assert {customer for bundle in bundles for customer in bundle} == membership
    assert sum(map(len, bundles)) == len(membership)
    assert set(bundles[0]).isdisjoint(bundles[1])


def test_weak_component_partition_keeps_isolated_seed_singleton() -> None:
    graph = _manual_graph((1, 2, 3), (_edge(1, 2, 0),))

    bundles = operators._native_cascade_weak_components(
        graph, {1, 2, 3}, (3, 1, 2)
    )

    assert bundles == [[3], [1, 2]]


def test_native_seed_policy_rng_and_order_are_preserved_without_extra_calls() -> None:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    rng = RecordingRng(48)
    eligible = operators._served_customers(source)

    destroyed = operators.cascade_aware_removal(source, rng, data, config)
    context = active_removal_context(destroyed)
    assert context is not None

    assert eligible == sorted(set(source.get_van_customers() + source.get_drone_customers()))
    assert rng.calls == [("choice", tuple(eligible), 2, False)]
    assert context.customer_selection_order == (8, 5)
    assert context.deletion_attempt_order == (8, 5, 6, 7)


def test_native_removal_partition_snapshot_and_membership_contract() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 2)
    before_signature = source.cache_signature()

    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"], ids["same_anchor"]]),
        data,
        config,
    )
    context = active_removal_context(destroyed)
    bundles = destroyed.metadata["cascade_bundles"]
    assert context is not None

    assert source.cache_signature() == before_signature
    assert context.customer_selection_order == (
        ids["cross_drone_customer"],
        ids["same_anchor"],
    )
    assert context.deletion_attempt_order == (
        ids["cross_drone_customer"],
        ids["same_anchor"],
        ids["recovery_anchor"],
        ids["same_drone_customer"],
    )
    assert [list(bundle.customer_ids) for bundle in bundles] == [
        sorted([ids["recovery_anchor"], ids["cross_drone_customer"]]),
        sorted([ids["same_anchor"], ids["same_drone_customer"]]),
    ]
    assert all(bundle.customer_ids == tuple(sorted(bundle.customer_ids)) for bundle in bundles)
    assert all(bundle.dependency_order == bundle.customer_ids for bundle in bundles)
    assert all(bundle.captured_before_removal for bundle in bundles)
    assert set(destroyed.unassigned) - set(source.unassigned) == set(
        destroyed.metadata["cascade_removed"]
    )


def test_implicit_sortie_side_effect_is_covered_by_r_star() -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)

    destroyed = operators.cascade_aware_removal(
        source,
        FixedChoiceRng([ids["cross_drone_customer"]]),
        data,
        config,
    )

    assert destroyed.metadata["cascade_removed"] == sorted(
        [ids["cross_drone_customer"], ids["recovery_anchor"]]
    )
    assert set(destroyed.unassigned) - set(source.unassigned) == set(
        destroyed.metadata["cascade_removed"]
    )


def test_atomic_validation_failure_discards_working_copy_and_context(monkeypatch) -> None:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    before_signature = source.cache_signature()
    before_metadata = source.copy().metadata
    authoritative_remove = operators._remove_customers

    def poisoned_remove(working, customers, **kwargs):
        result = authoritative_remove(working, customers, **kwargs)
        result.mark_unassigned(ids["plain_van_customer"])
        return result

    monkeypatch.setattr(operators, "_remove_customers", poisoned_remove)

    with pytest.raises(
        RemovalContextContractError, match="ATOMIC CO-REMOVAL CONTRACT VIOLATION"
    ):
        operators.cascade_aware_removal(
            source,
            FixedChoiceRng([ids["cross_drone_customer"]]),
            data,
            config,
        )

    assert source.cache_signature() == before_signature
    assert source.metadata == before_metadata
    assert active_removal_context(source) is None
    assert "cascade_contract" not in source.metadata


def test_cascade_dependency_compatibility_query_uses_customer_only_graph() -> None:
    _, _, source, ids = _coordinated_fixture()

    assert operators._cascade_dependencies(source, ids["cross_drone_customer"]) == {
        ids["cross_drone_customer"],
        ids["recovery_anchor"],
    }
    assert operators._cascade_dependencies(source, ids["plain_van_customer"]) == {
        ids["plain_van_customer"]
    }
