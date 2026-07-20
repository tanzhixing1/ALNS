from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import operators
from feasibility import check_solution_feasible
from objective import objective
from operator_modes import OperatorMode, paper_action_registry
from removal_structural_context import active_removal_context, capture_structural_projection
from tests.test_stage2d0_cascade_contract import _coordinated_fixture, _set_destroy_count
from tests.test_stage2ea1_structural_context import (
    CANDIDATE_TRACE_BASELINE,
    PAIR_BASELINE,
    _business_fingerprint,
    _stable_diagnostic,
)


OUTPUT_DIR = Path(__file__).resolve().parent
FIXTURE = "Stage 2D coordinated fixture (8 customers, removal count 1)"
SEED = 29

DESTROYS = (
    ("Random", "random_customer_removal", operators.random_customer_removal),
    ("Greedy", "greedy_removal", operators.greedy_removal),
    ("Related", "related_customer_removal", operators.related_customer_removal),
    ("Cascade", "cascade_aware_removal", operators.cascade_aware_removal),
)
REPAIRS = (
    ("Global", "best_mode_repair", operators.best_mode_repair),
    ("Local", "greedy_van_repair", operators.greedy_van_repair),
    ("Regret", "regret_repair", operators.regret_repair),
    ("Cascade", "cascade_repair", operators.cascade_repair),
)

ORDINARY_CASCADE_BASELINE = {
    "Random+Cascade": (
        927.880274815561,
        "56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e",
        True,
        "success",
    ),
    "Greedy+Cascade": (
        791.639335388478,
        "b29d4743a67273b3908cd26e1f4a95c634829d3a50aae1cc7596cf5803ee5cb3",
        True,
        "success",
    ),
    "Related+Cascade": (
        927.880274815561,
        "56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e",
        True,
        "success",
    ),
}
EXPECTED_ORDINARY_SELECTION = {
    "Random": ([12], [12]),
    "Greedy": ([7], [7]),
    "Related": ([12], [12]),
}
EXPECTED_RNG_DIGEST = {
    "Random": "6d5f81475e1e419dfbf72367d4d3b0ef26a57b5668b320d82f98ba052018cce1",
    "Greedy": "6b1deb4fb11923d5a698f8b90d6e2cc7b2e247c417c329dbbdee14e0e1854292",
    "Related": "6d5f81475e1e419dfbf72367d4d3b0ef26a57b5668b320d82f98ba052018cce1",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(_jsonable(item) for item in value)
    return value


class AuditRng:
    def __init__(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)
        self.calls: list[dict[str, Any]] = []

    @property
    def bit_generator(self):
        return self._rng.bit_generator

    def _record(self, method: str, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any):
        self.calls.append(
            {
                "method": method,
                "args": _jsonable(args),
                "kwargs": _jsonable(kwargs),
                "result": _jsonable(result),
            }
        )
        return result

    def choice(self, *args, **kwargs):
        return self._record("choice", args, kwargs, self._rng.choice(*args, **kwargs))

    def random(self, *args, **kwargs):
        return self._record("random", args, kwargs, self._rng.random(*args, **kwargs))

    def integers(self, *args, **kwargs):
        return self._record("integers", args, kwargs, self._rng.integers(*args, **kwargs))

    def uniform(self, *args, **kwargs):
        return self._record("uniform", args, kwargs, self._rng.uniform(*args, **kwargs))

    def permutation(self, *args, **kwargs):
        return self._record(
            "permutation", args, kwargs, self._rng.permutation(*args, **kwargs)
        )

    def shuffle(self, *args, **kwargs):
        result = self._rng.shuffle(*args, **kwargs)
        return self._record("shuffle", args, kwargs, result)


def _rng_digest(rng: AuditRng) -> str:
    payload = json.dumps(
        _jsonable(rng.bit_generator.state), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bundle_row(bundle) -> dict[str, Any]:
    return {
        "bundle_id": bundle.bundle_id,
        "customer_ids": list(bundle.customer_ids),
        "dependency_order": list(bundle.dependency_order),
        "contract_fingerprint": bundle.contract_fingerprint(),
        "captured_before_removal": bool(bundle.captured_before_removal),
        "affected_route_segment_ids": list(
            bundle.affected_structure_scope.van_route_segment_ids
        ),
        "drone_subroute_ids": list(bundle.affected_structure_scope.drone_subroute_ids),
    }


def _baseline_for(pair_name: str, destroy_name: str, repair_name: str):
    if destroy_name != "Cascade" and repair_name == "Cascade":
        return ORDINARY_CASCADE_BASELINE[pair_name]
    return PAIR_BASELINE[pair_name]


def _expected_category(destroy_name: str, repair_name: str) -> str:
    if destroy_name == "Greedy":
        return "A"
    if repair_name in {"Regret", "Cascade"}:
        return "A"
    return "B"


def run_pair(
    action_id: int,
    destroy_name: str,
    destroy_key: str,
    destroy,
    repair_name: str,
    repair_key: str,
    repair,
    run: int,
) -> dict[str, Any]:
    config, data, source, _ = _coordinated_fixture()
    _set_destroy_count(config, data, 1)
    rng = AuditRng(SEED)
    source_signature = source.cache_signature()
    graph = operators._build_native_cascade_customer_dependency_graph(
        capture_structural_projection(source), data.customers
    )
    graph_edges = [
        {
            "predicate_id": edge.predicate_id,
            "source": edge.source_customer,
            "target": edge.target_customer,
            "rank": list(edge.structural_rank),
            "provenance": edge.provenance,
        }
        for edge in graph.edges
    ]
    pair_name = f"{destroy_name}+{repair_name}"
    row: dict[str, Any] = {
        "run": run,
        "action_id": action_id,
        "destroy": destroy_name,
        "destroy_key": destroy_key,
        "repair": repair_name,
        "repair_key": repair_key,
        "pair": pair_name,
        "fixture": FIXTURE,
        "seed": SEED,
        "operator_mode": config.alns.operator_mode,
        "eligible_customer_ids": operators._served_customers(source),
        "requested_removal_count": 1,
    }
    adapter_calls: list[dict[str, Any]] = []
    original_adapter = operators.adapt_removal_context_to_cascade_bundles

    def recording_adapter(context, state, **kwargs):
        bundles = original_adapter(context, state, **kwargs)
        adapter_calls.append(
            {
                "source_operator": context.source_destroy_operator,
                "bundles": [_bundle_row(bundle) for bundle in bundles],
            }
        )
        return bundles

    try:
        destroyed = destroy(source, rng, data, config)
        context = active_removal_context(destroyed)
        assert context is not None
        native = destroy_name == "Cascade"
        input_bundles = (
            [_bundle_row(bundle) for bundle in destroyed.metadata["cascade_bundles"]]
            if native
            else []
        )
        r_star = sorted(int(customer) for customer in context.actually_unassigned_customer_ids)
        induced_edges = [
            edge
            for edge in graph_edges
            if edge["source"] in r_star and edge["target"] in r_star
        ]
        row.update(
            {
                "context_path": "Native" if native else "Ordinary",
                "destroy_selected_customers": list(context.customer_selection_order),
                "selected_removed_customer_ids": list(
                    context.selected_removed_customer_ids
                ),
                "actually_unassigned": list(context.actually_unassigned_customer_ids),
                "deletion_attempt_order": list(context.deletion_attempt_order),
                "actual_unassignment_order": list(context.actual_unassignment_order),
                "r_star": r_star if native else [],
                "closure_discovery_order": (
                    list(context.deletion_attempt_order) if native else []
                ),
                "dependency_trace": [
                    list(edge) for edge in context.cascade_dependency_trace
                ],
                "dependency_edges": induced_edges if native else [],
                "dependency_predicate_hits": (
                    dict(Counter(edge["predicate_id"] for edge in induced_edges))
                    if native
                    else {}
                ),
                "native_partition_evidence": [
                    list(bundle)
                    for bundle in context.cascade_native_partition_evidence
                ],
                "repair_input_bundles": input_bundles,
                "active_context_before_repair": True,
                "rng_calls_after_destroy": list(rng.calls),
                "rng_digest_after_destroy": _rng_digest(rng),
                "caller_state_unchanged_after_destroy": (
                    source.cache_signature() == source_signature
                ),
            }
        )

        trace: list[Any] = []
        kwargs = (
            {"trace_collector": trace.append}
            if repair_name in {"Local", "Regret"}
            else {}
        )
        operators.adapt_removal_context_to_cascade_bundles = recording_adapter
        try:
            repaired = repair(destroyed, rng, data, config, **kwargs)
        finally:
            operators.adapt_removal_context_to_cascade_bundles = original_adapter

        cost, _ = objective(repaired, data, config)
        feasible, violations = check_solution_feasible(repaired, data, config)
        diagnostics = repaired.metadata.get("cascade_repair_diagnostics", {})
        status = str(diagnostics.get("status", "returned"))
        reason = str(diagnostics.get("reason", ""))
        if "missing cascade contract" in reason or "rejected context" in reason:
            category = "C"
        elif status == "failure" or not feasible:
            category = "B"
        else:
            category = "A"
        fingerprint = _business_fingerprint(repaired)
        baseline = _baseline_for(pair_name, destroy_name, repair_name)
        expected_cost, expected_fingerprint, expected_feasible, expected_status = baseline
        candidate_trace_digest = (
            hashlib.sha256(repr(_stable_diagnostic(trace)).encode()).hexdigest()
            if trace
            else ""
        )
        row.update(
            {
                "adapter_call_count": len(adapter_calls),
                "adapter_output_bundles": (
                    adapter_calls[0]["bundles"] if adapter_calls else []
                ),
                "bundle_count": len(
                    input_bundles
                    if native
                    else (adapter_calls[0]["bundles"] if adapter_calls else [])
                ),
                "repair_result_category": category,
                "expected_category": _expected_category(destroy_name, repair_name),
                "repair_status": status,
                "repair_reason": reason,
                "objective": cost,
                "feasible": feasible,
                "violations": sorted(str(item) for item in violations),
                "active_context_after_repair": active_removal_context(repaired) is not None,
                "active_context_on_destroyed_after_repair": (
                    active_removal_context(destroyed) is not None
                ),
                "active_context_on_source_after_repair": (
                    active_removal_context(source) is not None
                ),
                "business_fingerprint": fingerprint,
                "candidate_trace_digest": candidate_trace_digest,
                "rng_calls_after_repair": list(rng.calls),
                "rng_digest_after_repair": _rng_digest(rng),
                "caller_state_unchanged_after_repair": (
                    source.cache_signature() == source_signature
                ),
                "baseline_expected": {
                    "objective": expected_cost,
                    "business_fingerprint": expected_fingerprint,
                    "feasible": expected_feasible,
                    "repair_status": expected_status,
                },
                "business_baseline_match": (
                    abs(cost - expected_cost) <= 1e-9
                    and fingerprint == expected_fingerprint
                    and feasible is expected_feasible
                    and status == expected_status
                ),
            }
        )
        if destroy_name != "Cascade":
            expected_selected, expected_actual = EXPECTED_ORDINARY_SELECTION[destroy_name]
            expected_trace = CANDIDATE_TRACE_BASELINE.get(pair_name, "")
            row["ordinary_hard_baseline_match"] = (
                row["business_baseline_match"]
                and row["destroy_selected_customers"] == expected_selected
                and row["actually_unassigned"] == expected_actual
                and row["rng_digest_after_repair"] == EXPECTED_RNG_DIGEST[destroy_name]
                and (not expected_trace or candidate_trace_digest == expected_trace)
                and row["context_path"] == "Ordinary"
                and not row["active_context_after_repair"]
                and not row["active_context_on_destroyed_after_repair"]
                and not row["active_context_on_source_after_repair"]
            )
        else:
            row["ordinary_hard_baseline_match"] = None
    except BaseException as exc:
        operators.adapt_removal_context_to_cascade_bundles = original_adapter
        row.update(
            {
                "repair_result_category": "D",
                "expected_category": _expected_category(destroy_name, repair_name),
                "exception": f"{type(exc).__name__}: {exc}",
                "adapter_call_count": len(adapter_calls),
                "active_context_on_source_after_repair": (
                    active_removal_context(source) is not None
                ),
                "caller_state_unchanged_after_repair": (
                    source.cache_signature() == source_signature
                ),
            }
        )
    return row


def main() -> None:
    registry = paper_action_registry(
        operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS
    )
    registry_rows = [
        {
            "action_id": item.action_id,
            "destroy_key": item.destroy_name,
            "repair_key": item.repair_name,
        }
        for item in registry.actions
    ]
    rows = []
    for run in (1, 2):
        for destroy_index, (destroy_name, destroy_key, destroy) in enumerate(DESTROYS):
            for repair_index, (repair_name, repair_key, repair) in enumerate(REPAIRS):
                action_id = destroy_index * 4 + repair_index
                rows.append(
                    run_pair(
                        action_id,
                        destroy_name,
                        destroy_key,
                        destroy,
                        repair_name,
                        repair_key,
                        repair,
                        run,
                    )
                )

    determinism: dict[str, bool] = {}
    for pair in sorted({row["pair"] for row in rows}):
        pair_rows = [row for row in rows if row["pair"] == pair]
        left = {key: value for key, value in pair_rows[0].items() if key != "run"}
        right = {key: value for key, value in pair_rows[1].items() if key != "run"}
        determinism[pair] = left == right

    first_runs = [row for row in rows if row["run"] == 1]
    categories = Counter(row["repair_result_category"] for row in first_runs)
    summary = {
        "fixture": FIXTURE,
        "seed": SEED,
        "operator_mode_enum": OperatorMode.PAPER.value,
        "registry": registry_rows,
        "category_counts": {
            key: categories.get(key, 0) for key in ("A", "B", "C", "D")
        },
        "all_categories_expected": all(
            row["repair_result_category"] == row["expected_category"]
            for row in first_runs
        ),
        "ordinary_12_hard_baseline_matches": sum(
            row.get("ordinary_hard_baseline_match") is True for row in first_runs
        ),
        "ordinary_12_mismatches": [
            row["pair"]
            for row in first_runs
            if row["destroy"] != "Cascade"
            and row.get("ordinary_hard_baseline_match") is not True
        ],
        "native_4_business_baseline_matches": sum(
            row.get("business_baseline_match") is True
            for row in first_runs
            if row["destroy"] == "Cascade"
        ),
        "determinism": determinism,
        "all_deterministic": all(determinism.values()),
        "all_contexts_clean": all(
            not row.get("active_context_after_repair", True)
            and not row.get("active_context_on_destroyed_after_repair", True)
            and not row.get("active_context_on_source_after_repair", True)
            for row in first_runs
        ),
        "native_adapter_calls": sum(
            row.get("adapter_call_count", 0)
            for row in first_runs
            if row["destroy"] == "Cascade"
        ),
        "ordinary_cascade_adapter_calls": sum(
            row.get("adapter_call_count", 0)
            for row in first_runs
            if row["destroy"] != "Cascade" and row["repair"] == "Cascade"
        ),
    }
    target = OUTPUT_DIR / "stage2f2_pair_runs.json"
    target.write_text(
        json.dumps({"summary": summary, "runs": rows}, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print(target)


if __name__ == "__main__":
    main()
