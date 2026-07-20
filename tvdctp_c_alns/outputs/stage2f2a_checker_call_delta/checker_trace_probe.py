from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any


EXPECTED = {
    "paper_mode": {
        "objective_calls": 653,
        "baseline_checker_calls": 909,
        "current_checker_calls": 910,
        "final_objective": 789.5462929944308,
        "final_fingerprint": "9de8f7ba48e3e29c3d7853e257c3515f9c86b4749cc4ce0d0493e051465fe583",
        "rng_digest": "0ef1b46c0559070d2546d0261ec49177635ed842cdeb4b5fb8820c671da5bf3b",
    },
    "extended_mode": {
        "objective_calls": 608,
        "baseline_checker_calls": 884,
        "current_checker_calls": 885,
        "final_objective": 789.5462929944308,
        "final_fingerprint": "3f8ec1b603fbb1d564063ba9a2d432148c4252af93e0e6b9305a0097f46bbf0f",
        "rng_digest": "57273a01c37b67814e439fbf7d5f4617e124eda6c3020aefd905f3e09f4525d5",
    },
}


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, set):
        return sorted((_normalize(item) for item in value), key=repr)
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "canonical_json"):
        return json.loads(value.canonical_json())
    return repr(value)


def _digest(value: Any) -> str:
    payload = json.dumps(
        _normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _business_payload(state: Any) -> dict[str, Any]:
    fields = (
        "selected_transshipment",
        "truck_route",
        "tractor_routes",
        "container_routes",
        "van_routes",
        "drone_sorties",
        "service_mode",
        "unassigned",
        "order_assignment",
        "container_assignment",
    )
    payload = {name: getattr(state, name, None) for name in fields}
    metadata = getattr(state, "metadata", {})
    payload["business_metadata"] = {
        "route_endpoints": metadata.get("route_endpoints", ()),
        "warehouse_ready_time": metadata.get("warehouse_ready_time", {}),
    }
    return _normalize(payload)


def _state_summary(state: Any, context_key: str) -> dict[str, Any]:
    metadata = getattr(state, "metadata", {})
    context = metadata.get(context_key)
    routes = getattr(state, "van_routes", {})
    sorties = getattr(state, "drone_sorties", [])
    cascade_diagnostics = metadata.get("cascade_repair_diagnostics")
    if isinstance(cascade_diagnostics, dict):
        cascade_diagnostics = {
            key: value
            for key, value in cascade_diagnostics.items()
            if "time" not in str(key).lower()
        }
    return {
        # Use the same business-only identity as the frozen Stage 2E.1 tests.
        # It excludes timing fields that the canonical checker legitimately refreshes.
        "business_fingerprint": hashlib.sha256(
            repr(state.cache_signature()).encode("utf-8")
        ).hexdigest(),
        "unassigned": sorted(int(item) for item in getattr(state, "unassigned", [])),
        "route_summary": _normalize(routes),
        "sortie_summary": _normalize(sorties),
        "active_context_present": context is not None,
        "context_type": type(context).__name__ if context is not None else None,
        "state_object_type": type(state).__name__,
        "cascade_repair_diagnostics": _normalize(cascade_diagnostics),
    }


def _rng_fingerprint(rng: Any) -> str | None:
    if rng is None:
        return None
    return _digest(rng.bit_generator.state)


def _relative_file(filename: str, source_root: Path) -> str:
    try:
        return str(Path(filename).resolve().relative_to(source_root.resolve())).replace("\\", "/")
    except ValueError:
        return Path(filename).name


def _classify_state(phase: str, caller_file: str, caller_function: str) -> str:
    if caller_file == "alns_solver.py" and caller_function == "run_c_alns":
        if phase == "initial_final_validation":
            return "initial"
        if phase == "final_best_validation":
            return "best"
    if caller_file == "initial_solution.py":
        return "initial-construction working copy"
    if phase == "destroy":
        return "Path B/destroy working copy"
    if phase == "repair":
        return "repair candidate/working copy"
    if phase == "candidate_objective":
        return "iteration candidate"
    return "unclassified production State"


def run(version: str, mode_value: str, source_root: Path, output: Path) -> None:
    sys.path.insert(0, str(source_root))

    import alns_profile
    import alns_solver
    import feasibility
    import initial_solution
    import objective as objective_module
    import operators
    import removal_structural_context
    from config import build_config
    from dataset_loader import generate_toy_data
    from operator_modes import OperatorMode, build_action_registry

    mode = OperatorMode(mode_value)
    expected = EXPECTED[mode_value]
    context_key = removal_structural_context.ACTIVE_REMOVAL_CONTEXT_KEY
    registry = build_action_registry(
        mode, operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS
    )
    action_ids = {
        (action.destroy_name, action.repair_name): action.action_id
        for action in registry.actions
    }

    runtime: dict[str, Any] = {
        "iteration": 0,
        "destroy_name": None,
        "repair_name": None,
        "action_id": None,
        "rng": None,
    }
    trace: list[dict[str, Any]] = []
    rng_trace: list[Any] = []
    started = time.perf_counter_ns()

    original_checker = feasibility.check_solution_feasible
    original_enter = alns_solver.enter_operator_pair
    original_exit = alns_solver.exit_operator_pair
    original_choice = alns_solver._roulette_choice
    original_accept = alns_solver._accept

    def traced_enter(destroy_name: str, repair_name: str):
        runtime["iteration"] += 1
        runtime["destroy_name"] = destroy_name
        runtime["repair_name"] = repair_name
        runtime["action_id"] = action_ids[(destroy_name, repair_name)]
        return original_enter(destroy_name, repair_name)

    def traced_exit(*args, **kwargs):
        try:
            return original_exit(*args, **kwargs)
        finally:
            runtime["destroy_name"] = None
            runtime["repair_name"] = None
            runtime["action_id"] = None

    def traced_choice(rng, names, weights):
        runtime["rng"] = rng
        rng_trace.append(("choice_before", copy.deepcopy(rng.bit_generator.state)))
        selected = original_choice(rng, names, weights)
        rng_trace.append(("choice_after", copy.deepcopy(rng.bit_generator.state)))
        return selected

    def traced_accept(rng, *args):
        runtime["rng"] = rng
        rng_trace.append(("accept_before", copy.deepcopy(rng.bit_generator.state)))
        accepted = original_accept(rng, *args)
        rng_trace.append(("accept_after", copy.deepcopy(rng.bit_generator.state)))
        return accepted

    def traced_checker(state, data, config):
        frames = traceback.extract_stack(limit=20)[:-1]
        direct = frames[-1]
        direct_file = _relative_file(direct.filename, source_root)
        direct_basename = Path(direct.filename).name
        stack_pairs = [
            f"{_relative_file(frame.filename, source_root)}:{frame.name}"
            for frame in frames[-10:]
            if Path(frame.filename).name != Path(__file__).name
        ]
        repair_name = alns_profile.active_repair_name()
        if repair_name != "unscoped":
            phase = "repair"
        elif runtime["action_id"] is not None and direct_basename == "objective.py":
            phase = "candidate_objective"
        elif runtime["action_id"] is not None:
            phase = "destroy"
        elif direct_basename == "alns_solver.py" and direct.lineno < 200:
            phase = "initial_final_validation"
        elif direct_basename == "alns_solver.py":
            phase = "final_best_validation"
        elif direct_basename == "initial_solution.py":
            phase = "initial_solution"
        else:
            phase = "pre/post-loop helper"

        before = _state_summary(state, context_key)
        rng_before = _rng_fingerprint(runtime["rng"])
        objective_index = int(alns_profile._PROFILE.get("objective_calls", 0))
        result = original_checker(state, data, config)
        after = _state_summary(state, context_key)
        rng_after = _rng_fingerprint(runtime["rng"])
        feasible, violations = result
        trace.append(
            {
                "version": version,
                "mode": mode_value,
                "call_index": len(trace) + 1,
                "pytest_node_id": (
                    "tests/test_stage2e1_operator_modes.py::"
                    + (
                        "test_paper_search_work_matches_preimplementation_baseline"
                        if mode is OperatorMode.PAPER
                        else "test_explicit_extended_run_matches_preimplementation_baseline"
                    )
                ),
                "iteration": runtime["iteration"] if runtime["action_id"] is not None else None,
                "action_id": runtime["action_id"],
                "destroy_name": runtime["destroy_name"],
                "repair_name": runtime["repair_name"],
                "execution_phase": phase,
                "direct_caller_file": direct_file,
                "direct_caller_function": direct.name,
                "direct_caller_line": direct.lineno,
                "compact_stack_signature": " > ".join(stack_pairs),
                "state_business_fingerprint_before": before["business_fingerprint"],
                "state_business_fingerprint_after": after["business_fingerprint"],
                "state_object_type": before["state_object_type"],
                "unassigned_customer_ids": before["unassigned"],
                "unassigned_customer_ids_after": after["unassigned"],
                "route_summary": before["route_summary"],
                "route_summary_after": after["route_summary"],
                "sortie_summary": before["sortie_summary"],
                "sortie_summary_after": after["sortie_summary"],
                "active_context_present": before["active_context_present"],
                "active_context_present_after": after["active_context_present"],
                "context_type": before["context_type"],
                "state_classification": _classify_state(phase, direct_basename, direct.name),
                "cascade_repair_diagnostics": before["cascade_repair_diagnostics"],
                "checker_result": bool(feasible),
                "normalized_violation_signature": _digest(sorted(str(item) for item in violations)),
                "violations": sorted(str(item) for item in violations),
                "rng_state_fingerprint_before": rng_before,
                "rng_state_fingerprint_after": rng_after,
                "objective_call_index": objective_index,
                "relative_order": len(trace) + 1,
                "relative_time_ns": time.perf_counter_ns() - started,
            }
        )
        return result

    aliases = [
        (feasibility, "check_solution_feasible"),
        (initial_solution, "check_solution_feasible"),
        (objective_module, "check_solution_feasible"),
        (operators, "check_solution_feasible"),
        (alns_solver, "check_solution_feasible"),
    ]
    originals = [(module, name, getattr(module, name)) for module, name in aliases]
    for module, name in aliases:
        setattr(module, name, traced_checker)
    alns_solver.enter_operator_pair = traced_enter
    alns_solver.exit_operator_pair = traced_exit
    alns_solver._roulette_choice = traced_choice
    alns_solver._accept = traced_accept

    try:
        config = build_config(
            num_customers=10,
            num_orders=10,
            num_transshipments=2,
            num_containers=1,
            iterations=12,
            seed=42,
            max_no_improve=100,
            early_stop_enabled=False,
            collect_full_candidate_diagnostics=True,
            operator_mode=mode,
        )
        data = generate_toy_data(config)
        config.alns.random_seed = 29
        result = alns_solver.run_c_alns(data, config)
    finally:
        for module, name, original in originals:
            setattr(module, name, original)
        alns_solver.enter_operator_pair = original_enter
        alns_solver.exit_operator_pair = original_exit
        alns_solver._roulette_choice = original_choice
        alns_solver._accept = original_accept

    rng_payload = json.dumps(rng_trace, sort_keys=True, separators=(",", ":"))
    rng_digest = hashlib.sha256(rng_payload.encode("utf-8")).hexdigest()
    final_fingerprint = hashlib.sha256(
        repr(result.best_state.cache_signature()).encode("utf-8")
    ).hexdigest()
    final_objective = objective_module.objective(result.best_state, data, config)[0]
    expected_checker = expected[f"{version}_checker_calls"]
    outcome = {
        "version": version,
        "mode": mode_value,
        "source_root": str(source_root.resolve()),
        "trace_count": len(trace),
        "profile_checker_calls": result.profile["check_solution_feasible_calls"],
        "profile_objective_calls": result.profile["objective_calls"],
        "history": [
            {
                "iteration": row["iteration"],
                "destroy": row["destroy"],
                "repair": row["repair"],
                "action_id": row["action_id"],
                "accepted": row["accepted"],
                "candidate_feasible": row["candidate_feasible"],
            }
            for row in result.history
        ],
        "rng_digest": rng_digest,
        "final_objective": final_objective,
        "final_fingerprint": final_fingerprint,
        "behavior_neutral_checks": {
            "trace_count_equals_profile": len(trace) == result.profile["check_solution_feasible_calls"],
            "checker_count_matches_expected": result.profile["check_solution_feasible_calls"] == expected_checker,
            "objective_calls_match_expected": result.profile["objective_calls"] == expected["objective_calls"],
            "rng_digest_matches_expected": rng_digest == expected["rng_digest"],
            "final_objective_matches_expected": abs(final_objective - expected["final_objective"]) <= 1e-9,
            "final_fingerprint_matches_expected": final_fingerprint == expected["final_fingerprint"],
            "checker_preserved_business_state": all(
                row["state_business_fingerprint_before"]
                == row["state_business_fingerprint_after"]
                for row in trace
            ),
            "checker_preserved_rng": all(
                row["rng_state_fingerprint_before"] == row["rng_state_fingerprint_after"]
                for row in trace
            ),
        },
        "trace": trace,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(outcome, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=("baseline", "current"), required=True)
    parser.add_argument("--mode", choices=("paper_mode", "extended_mode"), required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.version, args.mode, args.source_root, args.output)


if __name__ == "__main__":
    main()
