from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import operators
from feasibility import check_solution_feasible
from removal_structural_context import active_removal_context
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


def _run_case(name: str, requested_count: int, seed: int, run: int) -> dict:
    config, data, source, ids = _coordinated_fixture()
    _set_destroy_count(config, data, requested_count)
    feasible, violations = check_solution_feasible(source.copy(), data, config)
    assert feasible and not violations
    rng = RecordingRng(seed)
    initial_fingerprint = operators._state_business_fingerprint(source)

    destroyed = operators.cascade_aware_removal(source, rng, data, config)
    context = active_removal_context(destroyed)
    assert context is not None
    bundles, contract_errors = operators._validated_cascade_bundles(destroyed)
    final_removal = tuple(int(customer) for customer in destroyed.metadata["cascade_removed"])
    dependency_map = {
        str(customer): sorted(
            int(dependency)
            for dependency in operators._cascade_dependencies(source, customer)
        )
        for customer in final_removal
    }
    bundle_rows = [
        {
            "bundle_id": bundle.bundle_id,
            "customer_ids": list(bundle.customer_ids),
            "dependency_order": list(bundle.dependency_order),
            "dependency_order_semantics": bundle.dependency_order_semantics,
            "removed_drone_subroutes": [
                {
                    "sortie_id": snapshot.sortie_id,
                    "customer_ids": list(snapshot.customer_ids),
                    "launch_node": snapshot.launch_node,
                    "recovery_node": snapshot.recovery_node,
                }
                for snapshot in bundle.removed_drone_subroutes
            ],
            "affected_route_segment_ids": list(
                bundle.affected_structure_scope.van_route_segment_ids
            ),
        }
        for bundle in destroyed.metadata["cascade_bundles"]
    ]
    return {
        "fixture_name": name,
        "run": run,
        "seed": seed,
        "requested_removal_count": requested_count,
        "source_is_canonical_feasible": feasible,
        "fixture_ids": ids,
        "initial_state_fingerprint": initial_fingerprint,
        "served_customer_order": operators._served_customers(source),
        "rng_calls": [list(call) for call in rng.calls],
        "seed_customer": (
            context.customer_selection_order[0]
            if context.customer_selection_order
            else None
        ),
        "initial_selected_set": list(context.customer_selection_order),
        "dependency_expansion_sequence": [
            {"source": source_id, "new_customer": dependency_id}
            for source_id, dependency_id in context.cascade_dependency_trace
        ],
        "dependency_map_on_final_set": dependency_map,
        "final_removal_set_R_star": list(final_removal),
        "removal_order": list(context.removal_order),
        "deletion_attempt_order": list(context.deletion_attempt_order),
        "actual_unassignment_order": list(context.actual_unassignment_order),
        "bundle_partition": [row["customer_ids"] for row in bundle_rows],
        "dependency_order": [row["dependency_order"] for row in bundle_rows],
        "destroyed_state_fingerprint": operators._state_business_fingerprint(destroyed),
        "removal_structural_context": {
            "context_id": context.context_id,
            "source_destroy_operator": context.source_destroy_operator,
            "selected_removed_customer_ids": list(
                context.selected_removed_customer_ids
            ),
            "actually_unassigned_customer_ids": list(
                context.actually_unassigned_customer_ids
            ),
            "pre_destroy_structural_fingerprint": (
                context.pre_destroy_structural_fingerprint
            ),
            "post_destroy_structural_fingerprint": (
                context.post_destroy_structural_fingerprint
            ),
            "cascade_dependency_trace": [
                list(edge) for edge in context.cascade_dependency_trace
            ],
            "cascade_native_partition_evidence": [
                list(bundle)
                for bundle in context.cascade_native_partition_evidence
            ],
            "cascade_native_dependency_order": [
                list(bundle) for bundle in context.cascade_native_dependency_order
            ],
        },
        "cascade_repair_input_summary": {
            "contract_valid": bundles is not None,
            "contract_errors": contract_errors,
            "bundle_count": len(bundle_rows),
            "bundles": bundle_rows,
            "active_context_present": True,
            "contract_source_operator": destroyed.metadata["cascade_contract"][
                "source_operator"
            ],
        },
    }


def main() -> None:
    rows = [
        _run_case(name, requested_count, seed, run)
        for name, requested_count, seed in CASES
        for run in (1, 2)
    ]
    grouped = {}
    comparison_fields = (
        "initial_state_fingerprint",
        "rng_calls",
        "seed_customer",
        "initial_selected_set",
        "dependency_expansion_sequence",
        "final_removal_set_R_star",
        "removal_order",
        "bundle_partition",
        "dependency_order",
        "destroyed_state_fingerprint",
    )
    for name, _, _ in CASES:
        pair = [row for row in rows if row["fixture_name"] == name]
        grouped[name] = {
            field: pair[0][field] == pair[1][field] for field in comparison_fields
        }
        grouped[name]["all_required_fields_equal"] = all(
            grouped[name].values()
        )

    target = Path(__file__).with_name("current_behavior_raw.json")
    target.write_text(
        json.dumps({"runs": rows, "determinism": grouped}, indent=2),
        encoding="utf-8",
    )
    print(target)
    print(json.dumps(grouped, indent=2))


if __name__ == "__main__":
    main()
