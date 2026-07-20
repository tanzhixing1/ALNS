from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if dataclasses.is_dataclass(value):
        return _normalize(dataclasses.asdict(value))
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
    return repr(value)


def _digest(value: Any) -> str:
    payload = json.dumps(
        _normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _state_summary(state: Any, *, context_getter: Any) -> dict[str, Any]:
    context = context_getter(state)
    return {
        "business_fingerprint": hashlib.sha256(
            repr(state.cache_signature()).encode("utf-8")
        ).hexdigest(),
        "selected_transshipment": int(state.selected_transshipment),
        "truck_route": _normalize(state.truck_route),
        "van_routes": _normalize(state.van_routes),
        "drone_sorties": _normalize(state.drone_sorties),
        "service_mode": _normalize(state.service_mode),
        "unassigned": [int(customer) for customer in state.unassigned],
        "active_context_present": context is not None,
        "active_context": _normalize(context),
    }


def _bundle_summary(bundle: Any) -> dict[str, Any]:
    return {
        "bundle": _normalize(bundle),
        "canonical_json": bundle.canonical_json(),
        "contract_fingerprint": bundle.contract_fingerprint(),
    }


def run(version: str, mode_value: str, source_root: Path, output: Path) -> None:
    sys.path.insert(0, str(source_root))

    import alns_profile
    import alns_solver
    import operators
    import removal_structural_context
    from config import build_config
    from dataset_loader import generate_toy_data
    from operator_modes import OperatorMode, build_action_registry

    mode = OperatorMode(mode_value)
    original_destroy = operators.cascade_aware_removal
    original_repair = operators.cascade_repair
    original_restore = operators._restore_snapshot_strategy_state
    original_van_states = operators._van_block_strategy_states
    original_drone_states = operators._drone_bundle_strategy_states
    original_validate = operators._validate_cascade_candidate
    original_enumerate = operators._enumerate_bundle_reconstruction_strategies
    original_enter = alns_solver.enter_operator_pair
    original_exit = alns_solver.exit_operator_pair
    original_choice = alns_solver._roulette_choice
    original_accept = alns_solver._accept

    runtime: dict[str, Any] = {
        "iteration": None,
        "action_id": None,
        "destroy": None,
        "repair": None,
        "solver_rng": None,
    }
    action15: dict[str, Any] = {
        "destroy": None,
        "repair": None,
        "raw_candidates": [],
        "validations": [],
        "enumerations": [],
    }

    registry = build_action_registry(
        mode, operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS
    )
    action_ids = {
        (item.destroy_name, item.repair_name): item.action_id
        for item in registry.actions
    }

    def in_action15() -> bool:
        return runtime["action_id"] == 15

    def traced_enter(destroy_name: str, repair_name: str):
        runtime["iteration"] = int(runtime["iteration"] or 0) + 1
        runtime["action_id"] = action_ids[(destroy_name, repair_name)]
        runtime["destroy"] = destroy_name
        runtime["repair"] = repair_name
        return original_enter(destroy_name, repair_name)

    def traced_exit(*args, **kwargs):
        try:
            return original_exit(*args, **kwargs)
        finally:
            runtime["action_id"] = None
            runtime["destroy"] = None
            runtime["repair"] = None

    def traced_choice(rng, names, weights):
        runtime["solver_rng"] = rng
        return original_choice(rng, names, weights)

    def traced_accept(rng, *args):
        runtime["solver_rng"] = rng
        return original_accept(rng, *args)

    def traced_destroy(state, rng, data, config):
        capture = in_action15()
        before = _state_summary(
            state, context_getter=removal_structural_context.active_removal_context
        )
        projection = removal_structural_context.capture_structural_projection(state)
        if hasattr(operators, "_build_native_cascade_customer_dependency_graph"):
            graph = operators._build_native_cascade_customer_dependency_graph(
                projection, data.customers
            )
            graph_record = {
                "kind": "native_ranked_graph",
                "customer_ids": list(graph.customer_ids),
                "edges": [_normalize(edge) for edge in graph.edges],
            }
        else:
            graph_record = {
                "kind": "legacy_dependency_query",
                "outgoing": {
                    str(customer): sorted(
                        int(item) for item in operators._cascade_dependencies(state, customer)
                    )
                    for customer in data.customers
                },
            }
        rng_before = _digest(rng.bit_generator.state)
        result = original_destroy(state, rng, data, config)
        rng_after = _digest(rng.bit_generator.state)
        context = removal_structural_context.active_removal_context(result)
        bundles = result.metadata.get("cascade_bundles", [])
        removed = [int(customer) for customer in result.metadata.get("cascade_removed", [])]
        initial_unassigned = set(before["unassigned"])
        if capture:
            action15["destroy"] = {
            "iteration": runtime["iteration"],
            "input_state": before,
            "pre_destroy_projection": _normalize(projection),
            "dependency_graph": graph_record,
            "rng_before": rng_before,
            "rng_after": rng_after,
            "rng_changed": rng_before != rng_after,
            "seed_order": (
                list(context.customer_selection_order) if context is not None else None
            ),
            "dependency_trace": (
                _normalize(context.cascade_dependency_trace)
                if context is not None
                else None
            ),
            "r_star": removed,
            "closure_or_deletion_order": (
                list(context.deletion_attempt_order) if context is not None else None
            ),
            "actual_unassignment_order": (
                list(context.actual_unassignment_order) if context is not None else None
            ),
            "actual_newly_unassigned": sorted(
                set(int(customer) for customer in result.unassigned) - initial_unassigned
            ),
            "bundles": [_bundle_summary(bundle) for bundle in bundles],
            "cascade_contract": _normalize(result.metadata.get("cascade_contract")),
            "removal_context": _normalize(context),
            "output_state": _state_summary(
                result,
                context_getter=removal_structural_context.active_removal_context,
            ),
            }
        return result

    def traced_restore(state, bundle, metrics):
        result = original_restore(state, bundle, metrics)
        if in_action15():
            action15["raw_candidates"].append(
                {
                    "source_kind": "snapshot",
                    "bundle_id": bundle.bundle_id,
                    "bundle_customer_ids": list(bundle.customer_ids),
                    "result": (
                        _state_summary(
                            result,
                            context_getter=removal_structural_context.active_removal_context,
                        )
                        if result is not None
                        else None
                    ),
                }
            )
        return result

    def traced_van_states(state, bundle, data, metrics):
        results = original_van_states(state, bundle, data, metrics)
        if in_action15():
            action15["raw_candidates"].append(
                {
                    "source_kind": "van_block",
                    "bundle_id": bundle.bundle_id,
                    "count": len(results),
                    "results": [
                        _state_summary(
                            item,
                            context_getter=removal_structural_context.active_removal_context,
                        )
                        for item in results
                    ],
                }
            )
        return results

    def traced_drone_states(state, bundle, data, config, metrics):
        results = original_drone_states(state, bundle, data, config, metrics)
        if in_action15():
            action15["raw_candidates"].append(
                {
                    "source_kind": "drone_bundle",
                    "bundle_id": bundle.bundle_id,
                    "count": len(results),
                    "results": [
                        _state_summary(
                            item,
                            context_getter=removal_structural_context.active_removal_context,
                        )
                        for item in results
                    ],
                }
            )
        return results

    def traced_validate(state, **kwargs):
        before = _state_summary(
            state, context_getter=removal_structural_context.active_removal_context
        )
        profile_before = {
            "objective_calls": int(alns_profile._PROFILE.get("objective_calls", 0)),
            "checker_calls": int(
                alns_profile._PROFILE.get("check_solution_feasible_calls", 0)
            ),
        }
        result = original_validate(state, **kwargs)
        if in_action15():
            action15["validations"].append(
                {
                    "bundle_customers": sorted(kwargs["bundle_customers"]),
                    "allowed_unassigned": sorted(kwargs["allowed_unassigned"]),
                    "state_before": before,
                    "state_after": _state_summary(
                        state,
                        context_getter=removal_structural_context.active_removal_context,
                    ),
                    "valid": bool(result[0]),
                    "violations": list(result[1]),
                    "profile_before": profile_before,
                    "profile_after": {
                        "objective_calls": int(
                            alns_profile._PROFILE.get("objective_calls", 0)
                        ),
                        "checker_calls": int(
                            alns_profile._PROFILE.get(
                                "check_solution_feasible_calls", 0
                            )
                        ),
                    },
                }
            )
        return result

    def traced_enumerate(state, bundle, **kwargs):
        result = original_enumerate(state, bundle, **kwargs)
        if in_action15():
            strategies, row = result
            action15["enumerations"].append(
                {
                    "bundle_id": bundle.bundle_id,
                    "input_state": _state_summary(
                        state,
                        context_getter=removal_structural_context.active_removal_context,
                    ),
                    "allowed_unassigned": sorted(kwargs["allowed_unassigned"]),
                    "row": {
                        key: _normalize(value)
                        for key, value in row.items()
                        if "time" not in key
                    },
                    "feasible_strategies": [
                        {
                            "source_kind": strategy.source_kind,
                            "identity": _normalize(strategy.stable_identity()),
                            "state": _state_summary(
                                strategy.resulting_state,
                                context_getter=removal_structural_context.active_removal_context,
                            ),
                        }
                        for strategy in strategies
                    ],
                }
            )
        return result

    def traced_repair(state, rng, data, config):
        capture = in_action15()
        before = _state_summary(
            state, context_getter=removal_structural_context.active_removal_context
        )
        rng_before = _digest(rng.bit_generator.state)
        profile_before = {
            "objective_calls": int(alns_profile._PROFILE.get("objective_calls", 0)),
            "checker_calls": int(
                alns_profile._PROFILE.get("check_solution_feasible_calls", 0)
            ),
        }
        result = original_repair(state, rng, data, config)
        rng_after = _digest(rng.bit_generator.state)
        diagnostics = result.metadata.get("cascade_repair_diagnostics")
        if isinstance(diagnostics, dict):
            diagnostics = {
                key: value
                for key, value in diagnostics.items()
                if "time" not in str(key).lower()
            }
            if isinstance(diagnostics.get("bundles"), list):
                diagnostics["bundles"] = [
                    {
                        key: value
                        for key, value in row.items()
                        if "time" not in str(key).lower()
                    }
                    for row in diagnostics["bundles"]
                ]
        if capture:
            action15["repair"] = {
            "iteration": runtime["iteration"],
            "input_state": before,
            "rng_before": rng_before,
            "rng_after": rng_after,
            "rng_changed": rng_before != rng_after,
            "profile_before": profile_before,
            "profile_after": {
                "objective_calls": int(
                    alns_profile._PROFILE.get("objective_calls", 0)
                ),
                "checker_calls": int(
                    alns_profile._PROFILE.get("check_solution_feasible_calls", 0)
                ),
            },
            "diagnostics": _normalize(diagnostics),
            "returned_state": _state_summary(
                result,
                context_getter=removal_structural_context.active_removal_context,
            ),
            }
        return result

    operators.cascade_aware_removal = traced_destroy
    operators.cascade_repair = traced_repair
    operators._restore_snapshot_strategy_state = traced_restore
    operators._van_block_strategy_states = traced_van_states
    operators._drone_bundle_strategy_states = traced_drone_states
    operators._validate_cascade_candidate = traced_validate
    operators._enumerate_bundle_reconstruction_strategies = traced_enumerate
    operators.DESTROY_OPERATORS["cascade_aware_removal"] = traced_destroy
    operators.REPAIR_OPERATORS["cascade_repair"] = traced_repair
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
        operators.cascade_aware_removal = original_destroy
        operators.cascade_repair = original_repair
        operators._restore_snapshot_strategy_state = original_restore
        operators._van_block_strategy_states = original_van_states
        operators._drone_bundle_strategy_states = original_drone_states
        operators._validate_cascade_candidate = original_validate
        operators._enumerate_bundle_reconstruction_strategies = original_enumerate
        operators.DESTROY_OPERATORS["cascade_aware_removal"] = original_destroy
        operators.REPAIR_OPERATORS["cascade_repair"] = original_repair
        alns_solver.enter_operator_pair = original_enter
        alns_solver.exit_operator_pair = original_exit
        alns_solver._roulette_choice = original_choice
        alns_solver._accept = original_accept

    action15["solver_result"] = {
        "profile_objective_calls": result.profile["objective_calls"],
        "profile_checker_calls": result.profile["check_solution_feasible_calls"],
        "history_row": next(
            row for row in result.history if int(row["action_id"]) == 15
        ),
        "final_best_state": _state_summary(
            result.best_state,
            context_getter=removal_structural_context.active_removal_context,
        ),
    }
    payload = {
        "version": version,
        "mode": mode_value,
        "source_root": str(source_root.resolve()),
        "action15": action15,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=("baseline", "current"), required=True)
    parser.add_argument(
        "--mode", choices=("paper_mode", "extended_mode"), required=True
    )
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.version, args.mode, args.source_root, args.output)


if __name__ == "__main__":
    main()
