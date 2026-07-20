from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "stage2f2_strict_regression" / "stage2f2_audit_probe.py"

spec = importlib.util.spec_from_file_location("stage2f2_original_probe", SOURCE)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.OUTPUT_DIR = HERE

original_run_pair = probe.run_pair


def counted_run_pair(*args, **kwargs):
    counters = {"objective": 0, "checker": 0, "graph": 0}
    original_objective = probe.operators.objective
    original_checker = probe.operators.check_solution_feasible
    original_graph = probe.operators._build_native_cascade_customer_dependency_graph

    def counting_objective(*call_args, **call_kwargs):
        counters["objective"] += 1
        return original_objective(*call_args, **call_kwargs)

    def counting_checker(*call_args, **call_kwargs):
        counters["checker"] += 1
        return original_checker(*call_args, **call_kwargs)

    def counting_graph(*call_args, **call_kwargs):
        counters["graph"] += 1
        return original_graph(*call_args, **call_kwargs)

    probe.operators.objective = counting_objective
    probe.operators.check_solution_feasible = counting_checker
    probe.operators._build_native_cascade_customer_dependency_graph = counting_graph
    try:
        row = original_run_pair(*args, **kwargs)
    finally:
        probe.operators.objective = original_objective
        probe.operators.check_solution_feasible = original_checker
        probe.operators._build_native_cascade_customer_dependency_graph = original_graph

    row["objective_calls"] = counters["objective"]
    row["checker_calls"] = counters["checker"]
    # The inherited audit probe performs one read-only graph build before every
    # destroy for trace reporting. Calls beyond that are production-path calls.
    row["native_graph_production_calls"] = max(0, counters["graph"] - 1)
    return row


probe.run_pair = counted_run_pair
probe.main()

payload = json.loads((HERE / "stage2f2_pair_runs.json").read_text(encoding="utf-8"))
first = [row for row in payload["runs"] if row["run"] == 1]

columns = (
    "action_id", "destroy", "repair", "fixture", "seed",
    "eligible_customer_ids", "requested_removal_count", "destroy_selected_customers",
    "actually_unassigned", "context_path", "adapter_call_count", "bundle_count",
    "repair_input_bundles", "adapter_output_bundles", "native_partition_evidence",
    "deletion_attempt_order", "repair_result_category", "repair_status",
    "objective", "feasible", "violations", "business_fingerprint",
    "rng_calls_after_repair", "rng_digest_after_repair", "checker_calls",
    "objective_calls", "active_context_after_repair",
)
with (HERE / "02a_paper_16_pair_matrix.csv").open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    for row in first:
        writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key) for key in columns})

ordinary_columns = (
    "action_id", "pair", "destroy_selected_customers", "actually_unassigned",
    "context_path", "adapter_call_count", "adapter_output_bundles",
    "native_graph_production_calls", "repair_result_category", "repair_status",
    "objective", "feasible", "violations", "business_fingerprint",
    "business_baseline_match", "ordinary_hard_baseline_match",
    "rng_calls_after_repair", "rng_digest_after_repair",
    "active_context_after_repair", "checker_calls", "objective_calls",
)
with (HERE / "03a_ordinary_12_pair_diff.csv").open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=ordinary_columns)
    writer.writeheader()
    for row in first:
        if row["destroy"] != "Cascade":
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key) for key in ordinary_columns})

native_columns = (
    "action_id", "pair", "destroy_selected_customers", "dependency_predicate_hits",
    "dependency_edges", "closure_discovery_order", "r_star",
    "native_partition_evidence", "repair_input_bundles", "deletion_attempt_order",
    "actually_unassigned", "adapter_call_count", "repair_result_category",
    "repair_status", "checker_calls",
    "objective_calls", "objective", "feasible", "violations",
    "business_fingerprint", "business_baseline_match", "rng_calls_after_repair",
    "rng_digest_after_repair", "caller_state_unchanged_after_repair",
    "active_context_after_repair",
)
with (HERE / "04a_native_four_pair_trace.csv").open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=native_columns)
    writer.writeheader()
    for row in first:
        if row["destroy"] == "Cascade":
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key) for key in native_columns})
