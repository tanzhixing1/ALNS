from __future__ import annotations

import json

import operators
from removal_structural_context import active_removal_context, capture_structural_projection
from tests.test_stage2d0_cascade_contract import (
    RecordingRng,
    _coordinated_fixture,
    _set_destroy_count,
)


CASES = (
    ("single_cross_van_chain", 1, 1),
    ("same_sortie_duplicate_membership", 1, 23),
    ("two_dependency_chains_two_bundles", 2, 58),
    ("two_seed_two_chain_order", 2, 48),
)


def run_case(name: str, count: int, seed: int, run: int) -> dict:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, count)
    source_signature = source.cache_signature()
    projection = capture_structural_projection(source)
    graph = operators._build_native_cascade_customer_dependency_graph(
        projection, data.customers
    )
    rng = RecordingRng(seed)
    destroyed = operators.cascade_aware_removal(source, rng, data, config)
    context = active_removal_context(destroyed)
    assert context is not None
    return {
        "fixture": name,
        "run": run,
        "eligible": operators._served_customers(source),
        "requested_count": count,
        "rng_calls": [list(call) for call in rng.calls],
        "seed_order": list(context.customer_selection_order),
        "edge_trace": [
            {
                "predicate_id": edge.predicate_id,
                "source": edge.source_customer,
                "target": edge.target_customer,
                "rank": list(edge.structural_rank),
                "provenance": edge.provenance,
            }
            for edge in graph.edges
        ],
        "closure_trace": [list(edge) for edge in context.cascade_dependency_trace],
        "r_star": list(context.selected_removed_customer_ids),
        "discovery_removal_order": list(context.deletion_attempt_order),
        "actual_unassignment_order": list(context.actual_unassignment_order),
        "newly_unassigned": sorted(
            set(destroyed.unassigned) - set(source.unassigned)
        ),
        "bundles": [
            {
                "customer_ids": list(bundle.customer_ids),
                "dependency_order": list(bundle.dependency_order),
                "captured_before_removal": bundle.captured_before_removal,
            }
            for bundle in destroyed.metadata["cascade_bundles"]
        ],
        "source_unchanged": source.cache_signature() == source_signature,
        "destroyed_fingerprint": operators._state_business_fingerprint(destroyed),
        "contract_valid": operators.cascade_metadata_is_current(destroyed),
    }


def main() -> None:
    rows = [
        run_case(name, count, seed, run)
        for name, count, seed in CASES
        for run in (1, 2)
    ]
    comparisons = {}
    for name, _, _ in CASES:
        pair = [row for row in rows if row["fixture"] == name]
        comparisons[name] = pair[0] == {**pair[1], "run": pair[0]["run"]}
    print(json.dumps({"runs": rows, "pairwise_equal": comparisons}, indent=2))


if __name__ == "__main__":
    main()
