from __future__ import annotations

import argparse
import faulthandler
import functools
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

import alns_profile
import alns_solver
import feasibility as feasibility_module
import initial_solution as initial_solution_module
import objective as objective_module
import operators
from config import build_config
from dataset_loader import generate_toy_data
from operator_modes import OperatorMode, build_action_registry


RUN_START = 0.0
TRACE_FILE: Any = None
STACK_FILE: Any = None
MODE = OperatorMode.PAPER.value
CONTEXT: dict[str, Any] = {
    "iteration": None,
    "destroy_name": None,
    "repair_name": None,
    "action_id": None,
    "choice_slot": 0,
    "destroy_weight": None,
    "objective_calls": 0,
    "objective_seconds": 0.0,
    "checker_calls": 0,
    "checker_seconds": 0.0,
    "cascade_adapter_calls": 0,
    "cascade_adapter_seconds": 0.0,
    "cascade_enumeration_calls": 0,
    "cascade_enumeration_seconds": 0.0,
}
FIRST_OVER_30: dict[str, Any] | None = None
FIRST_OVER_60: dict[str, Any] | None = None
STACK_STOP = threading.Event()


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(item) for item in value]
    return repr(value)


def emit(event_type: str, *, phase: str, status: str, **fields: Any) -> None:
    now = time.perf_counter()
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_from_run_start": now - RUN_START,
        "event_type": event_type,
        "iteration": CONTEXT.get("iteration", "unavailable"),
        "operator_mode": MODE,
        "action_id": CONTEXT.get("action_id", "unavailable"),
        "destroy_name": CONTEXT.get("destroy_name", "unavailable"),
        "repair_name": CONTEXT.get("repair_name", "unavailable"),
        "phase": phase,
        "phase_start": fields.pop("phase_start", "unavailable"),
        "phase_end": fields.pop("phase_end", "unavailable"),
        "phase_seconds": fields.pop("phase_seconds", "unavailable"),
        "status": status,
        "exception": fields.pop("exception", ""),
        **fields,
    }
    TRACE_FILE.write(json.dumps(_safe(row), ensure_ascii=False, sort_keys=True) + "\n")
    TRACE_FILE.flush()


def _mark_slow_call(phase: str, seconds: float, start: float, end: float) -> None:
    global FIRST_OVER_30, FIRST_OVER_60
    record = {
        "iteration": CONTEXT.get("iteration"),
        "action_id": CONTEXT.get("action_id"),
        "destroy_name": CONTEXT.get("destroy_name"),
        "repair_name": CONTEXT.get("repair_name"),
        "phase": phase,
        "phase_start": start,
        "phase_end": end,
        "phase_seconds": seconds,
    }
    if seconds > 30.0 and FIRST_OVER_30 is None:
        FIRST_OVER_30 = dict(record)
        emit(
            "slow_call",
            phase=phase,
            status="over_30_seconds",
            **{key: value for key, value in record.items() if key != "phase"},
        )
    if seconds > 60.0 and FIRST_OVER_60 is None:
        FIRST_OVER_60 = dict(record)
        emit(
            "slow_call",
            phase=phase,
            status="over_60_seconds",
            **{key: value for key, value in record.items() if key != "phase"},
        )


def _profile_scalars(repair_name: str | None) -> dict[str, Any]:
    profile = getattr(alns_profile, "_PROFILE", {})
    repair = profile.get("repair", {}).get(repair_name or "", {})
    local = profile.get("local_feasibility_cache", {})
    return {
        "objective_call_count": int(profile.get("objective_calls", 0)),
        "checker_call_count": int(profile.get("check_solution_feasible_calls", 0)),
        "raw_candidate_count": int(repair.get("candidate_count", 0)),
        "hard_feasible_candidate_count": int(repair.get("feasible_candidate_count", 0)),
        "van_candidate_count": int(repair.get("van_candidate_count", 0)),
        "drone_candidate_count": int(repair.get("drone_candidate_count", 0)),
        "raw_drone_candidate_count": int(local.get("raw_drone_candidate_count", 0)),
        "unique_candidate_count": int(local.get("unique_candidates", 0)),
        "duplicate_candidate_count": int(local.get("duplicate_candidates_skipped", 0)),
    }


def _delta(after: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    return {key: int(after[key]) - int(before.get(key, 0)) for key in after}


def _reset_iteration_counters() -> None:
    for key in (
        "objective_calls",
        "checker_calls",
        "cascade_adapter_calls",
        "cascade_enumeration_calls",
    ):
        CONTEXT[key] = 0
    for key in (
        "objective_seconds",
        "checker_seconds",
        "cascade_adapter_seconds",
        "cascade_enumeration_seconds",
    ):
        CONTEXT[key] = 0.0


def _replace_module_references(original: Callable[..., Any], wrapped: Callable[..., Any]) -> None:
    for module in tuple(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if not path:
            continue
        try:
            if PACKAGE_ROOT not in Path(path).resolve().parents:
                continue
        except OSError:
            continue
        for name, value in tuple(vars(module).items()):
            if value is original:
                setattr(module, name, wrapped)


def _periodic_python_stack() -> None:
    """Persist stacks without invoking Windows' unstable delayed C callback."""
    while not STACK_STOP.wait(60.0):
        STACK_FILE.write("\nTimeout (0:01:00) - Python frame snapshot\n")
        for thread_id, frame in sys._current_frames().items():
            STACK_FILE.write(f"\nThread {thread_id:#x}:\n")
            traceback.print_stack(frame, file=STACK_FILE)
        STACK_FILE.flush()


def install_instrumentation() -> None:
    registry = build_action_registry(
        OperatorMode.PAPER, operators.DESTROY_OPERATORS, operators.REPAIR_OPERATORS
    )
    original_choice = alns_solver._roulette_choice

    @functools.wraps(original_choice)
    def traced_choice(rng: Any, names: list[str], weights: dict[str, float]) -> str:
        # The wrapper never reads from or calls the RNG. Only the original callable does.
        selected = original_choice(rng, names, weights)
        if CONTEXT["choice_slot"] == 0:
            CONTEXT["iteration"] = int(CONTEXT.get("iteration") or 0) + 1
            CONTEXT["destroy_name"] = selected
            CONTEXT["repair_name"] = None
            CONTEXT["action_id"] = None
            CONTEXT["destroy_weight"] = float(weights.get(selected, -1.0))
            CONTEXT["choice_slot"] = 1
            _reset_iteration_counters()
        else:
            CONTEXT["repair_name"] = selected
            CONTEXT["action_id"] = registry.action_id_for_pair(
                str(CONTEXT["destroy_name"]), selected
            )
            CONTEXT["choice_slot"] = 0
            emit(
                "selection",
                phase="operator_selection",
                status="complete",
                destroy_weight=CONTEXT.get("destroy_weight", "unavailable"),
                repair_weight=float(weights.get(selected, -1.0)),
            )
        return selected

    alns_solver._roulette_choice = traced_choice

    original_objective = objective_module.objective

    @functools.wraps(original_objective)
    def traced_objective(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return original_objective(*args, **kwargs)
        finally:
            ended = time.perf_counter()
            CONTEXT["objective_calls"] += 1
            CONTEXT["objective_seconds"] += ended - started
            _mark_slow_call("objective", ended - started, started, ended)

    _replace_module_references(original_objective, traced_objective)

    original_checker = feasibility_module.check_solution_feasible

    @functools.wraps(original_checker)
    def traced_checker(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return original_checker(*args, **kwargs)
        finally:
            ended = time.perf_counter()
            CONTEXT["checker_calls"] += 1
            CONTEXT["checker_seconds"] += ended - started
            _mark_slow_call("canonical_checker", ended - started, started, ended)

    _replace_module_references(original_checker, traced_checker)

    for name, original in tuple(operators.DESTROY_OPERATORS.items()):
        @functools.wraps(original)
        def traced_destroy(*args: Any, __name: str = name, __original: Callable[..., Any] = original, **kwargs: Any) -> Any:
            started = time.perf_counter()
            before = _profile_scalars(CONTEXT.get("repair_name"))
            emit("phase_start", phase="destroy", status="started", phase_start=started)
            try:
                result = __original(*args, **kwargs)
            except BaseException as exc:
                ended = time.perf_counter()
                emit("phase_end", phase="destroy", status="exception", phase_start=started, phase_end=ended, phase_seconds=ended-started, exception=repr(exc))
                raise
            ended = time.perf_counter()
            emit("phase_end", phase="destroy", status="complete", phase_start=started, phase_end=ended, phase_seconds=ended-started, profile_delta=_delta(_profile_scalars(CONTEXT.get("repair_name")), before))
            _mark_slow_call("destroy", ended - started, started, ended)
            return result
        operators.DESTROY_OPERATORS[name] = traced_destroy

    for name, original in tuple(operators.REPAIR_OPERATORS.items()):
        @functools.wraps(original)
        def traced_repair(*args: Any, __name: str = name, __original: Callable[..., Any] = original, **kwargs: Any) -> Any:
            started = time.perf_counter()
            before = _profile_scalars(__name)
            emit("phase_start", phase="repair", status="started", phase_start=started)
            try:
                result = __original(*args, **kwargs)
            except BaseException as exc:
                ended = time.perf_counter()
                emit("phase_end", phase="repair", status="exception", phase_start=started, phase_end=ended, phase_seconds=ended-started, exception=repr(exc))
                raise
            ended = time.perf_counter()
            diagnostics: dict[str, Any] = {}
            if __name == "cascade_repair":
                raw = getattr(result, "metadata", {}).get("cascade_repair_diagnostics", {})
                if isinstance(raw, dict):
                    bundles = raw.get("bundles", [])
                    diagnostics = {
                        "bundle_count": len(bundles) if isinstance(bundles, list) else "unavailable",
                        "status": raw.get("status", "unavailable"),
                        "reason": raw.get("reason", ""),
                        "state_copy_count": raw.get("state_copy_count", "unavailable"),
                        "objective_call_count": raw.get("objective_call_count", "unavailable"),
                        "checker_call_count": raw.get("checker_call_count", "unavailable"),
                        "enumeration_time": raw.get("enumeration_time", "unavailable"),
                        "scoring_time": raw.get("scoring_time", "unavailable"),
                        "adapter_time": raw.get("adapter_time", "unavailable"),
                        "bundle_rows": [
                            {
                                "bundle_id": row.get("bundle_id"),
                                "bundle_size": row.get("bundle_size"),
                                "raw_bundle_strategy_count": row.get("raw_bundle_strategy_count"),
                                "feasible_bundle_strategy_count": row.get("feasible_bundle_strategy_count"),
                                "unique_bundle_strategy_count": row.get("unique_bundle_strategy_count"),
                                "enumeration_time": row.get("enumeration_time"),
                                "scoring_time": row.get("scoring_time"),
                                "selected_strategy_identity": row.get("selected_strategy_identity"),
                            }
                            for row in bundles
                            if isinstance(row, dict)
                        ],
                    }
            emit("phase_end", phase="repair", status="complete", phase_start=started, phase_end=ended, phase_seconds=ended-started, selected_strategy=diagnostics.get("bundle_rows", "unavailable"), bundle_count=diagnostics.get("bundle_count", "unavailable"), repair_diagnostics=diagnostics or "unavailable", profile_delta=_delta(_profile_scalars(__name), before))
            _mark_slow_call("repair", ended - started, started, ended)
            return result
        operators.REPAIR_OPERATORS[name] = traced_repair

    original_adapter = operators.adapt_removal_context_to_cascade_bundles

    @functools.wraps(original_adapter)
    def traced_adapter(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        emit("phase_start", phase="cascade_adapter", status="started", phase_start=started)
        try:
            result = original_adapter(*args, **kwargs)
        except BaseException as exc:
            ended = time.perf_counter()
            emit("phase_end", phase="cascade_adapter", status="exception", phase_start=started, phase_end=ended, phase_seconds=ended-started, exception=repr(exc))
            raise
        ended = time.perf_counter()
        CONTEXT["cascade_adapter_calls"] += 1
        CONTEXT["cascade_adapter_seconds"] += ended - started
        emit("phase_end", phase="cascade_adapter", status="complete", phase_start=started, phase_end=ended, phase_seconds=ended-started, bundle_count=len(result), adapter_diagnostics=kwargs.get("diagnostics", "unavailable"))
        _mark_slow_call("cascade_adapter", ended - started, started, ended)
        return result

    operators.adapt_removal_context_to_cascade_bundles = traced_adapter

    original_enumeration = operators._enumerate_bundle_reconstruction_strategies

    @functools.wraps(original_enumeration)
    def traced_enumeration(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        emit("phase_start", phase="cascade_candidate_enumeration", status="started", phase_start=started)
        try:
            result = original_enumeration(*args, **kwargs)
        except BaseException as exc:
            ended = time.perf_counter()
            emit("phase_end", phase="cascade_candidate_enumeration", status="exception", phase_start=started, phase_end=ended, phase_seconds=ended-started, exception=repr(exc))
            raise
        ended = time.perf_counter()
        CONTEXT["cascade_enumeration_calls"] += 1
        CONTEXT["cascade_enumeration_seconds"] += ended - started
        row = result[1] if isinstance(result, tuple) and len(result) > 1 else {}
        emit("phase_end", phase="cascade_candidate_enumeration", status="complete", phase_start=started, phase_end=ended, phase_seconds=ended-started, raw_candidate_count=row.get("raw_bundle_strategy_count", "unavailable"), hard_feasible_candidate_count=row.get("feasible_bundle_strategy_count", "unavailable"), unique_candidate_count=row.get("unique_bundle_strategy_count", "unavailable"), bundle_count=1)
        _mark_slow_call("cascade_candidate_enumeration", ended - started, started, ended)
        return result

    operators._enumerate_bundle_reconstruction_strategies = traced_enumeration

    original_exit_pair = alns_solver.exit_operator_pair

    @functools.wraps(original_exit_pair)
    def traced_exit_pair(*args: Any, **kwargs: Any) -> Any:
        result = original_exit_pair(*args, **kwargs)
        now = time.perf_counter()
        emit("phase_summary", phase="objective", status="complete", phase_end=now, phase_seconds=CONTEXT["objective_seconds"], call_count=CONTEXT["objective_calls"])
        emit("phase_summary", phase="canonical_checker", status="complete", phase_end=now, phase_seconds=CONTEXT["checker_seconds"], call_count=CONTEXT["checker_calls"])
        emit("iteration_end", phase="iteration", status="complete", phase_end=now, phase_seconds="unavailable", objective_call_count=CONTEXT["objective_calls"], checker_call_count=CONTEXT["checker_calls"], cascade_adapter_call_count=CONTEXT["cascade_adapter_calls"], cascade_adapter_seconds=CONTEXT["cascade_adapter_seconds"], cascade_enumeration_call_count=CONTEXT["cascade_enumeration_calls"], cascade_enumeration_seconds=CONTEXT["cascade_enumeration_seconds"], pair_outcome=kwargs)
        return result

    alns_solver.exit_operator_pair = traced_exit_pair


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--stack", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    global RUN_START, TRACE_FILE, STACK_FILE
    args = parse_args()
    args.trace.parent.mkdir(parents=True, exist_ok=True)
    RUN_START = time.perf_counter()
    TRACE_FILE = args.trace.open("w", encoding="utf-8", buffering=1)
    STACK_FILE = args.stack.open("a", encoding="utf-8", buffering=1)
    STACK_FILE.write(f"\n===== {datetime.now(timezone.utc).isoformat()} iterations={args.iterations} =====\n")
    STACK_FILE.flush()
    faulthandler.enable(file=STACK_FILE, all_threads=True)
    stack_thread = threading.Thread(
        target=_periodic_python_stack,
        name="runtime-probe-stack-watchdog",
        daemon=True,
    )
    stack_thread.start()
    emit(
        "run_start",
        phase="runner",
        status="started",
        iterations_requested=args.iterations,
        fatal_handler="faulthandler.enable",
        periodic_stack_method="sys._current_frames",
    )
    install_instrumentation()
    config = build_config(
        num_customers=20,
        num_orders=20,
        num_transshipments=2,
        num_containers=2,
        iterations=args.iterations,
        seed=42,
        operator_mode=OperatorMode.PAPER,
    )
    config_payload = {
        "num_orders": config.data.num_orders,
        "num_customers": config.data.num_customers,
        "num_containers": config.data.num_containers,
        "num_transshipments": config.data.num_transshipments,
        "iterations": config.alns.max_iterations,
        "seed": config.alns.random_seed,
        "operator_mode": config.alns.operator_mode.value,
        "drones_per_van": config.fleet.drones_per_van,
        "max_drones_carried_per_van": config.fleet.max_drones_carried_per_van,
        "high_floor_ratio": config.data.high_floor_ratio,
        "max_no_improve": config.alns.max_no_improve,
        "early_stop_enabled": config.alns.early_stop_enabled,
    }
    emit("resolved_config", phase="config", status="complete", config=config_payload)
    try:
        started = time.perf_counter()
        emit("phase_start", phase="data_generation", status="started", phase_start=started)
        data = generate_toy_data(config)
        ended = time.perf_counter()
        emit("phase_end", phase="data_generation", status="complete", phase_start=started, phase_end=ended, phase_seconds=ended-started)

        original_initial = alns_solver.initial_solution

        @functools.wraps(original_initial)
        def traced_initial(*call_args: Any, **call_kwargs: Any) -> Any:
            initial_started = time.perf_counter()
            emit("phase_start", phase="initial_solution", status="started", phase_start=initial_started)
            try:
                state = original_initial(*call_args, **call_kwargs)
            except BaseException as exc:
                initial_ended = time.perf_counter()
                emit("phase_end", phase="initial_solution", status="exception", phase_start=initial_started, phase_end=initial_ended, phase_seconds=initial_ended-initial_started, exception=repr(exc))
                raise
            initial_ended = time.perf_counter()
            emit("phase_end", phase="initial_solution", status="complete", phase_start=initial_started, phase_end=initial_ended, phase_seconds=initial_ended-initial_started)
            return state

        alns_solver.initial_solution = traced_initial
        result = alns_solver.run_c_alns(data, config)
        emit("run_end", phase="runner", status="complete", iterations_requested=args.iterations, iterations_completed=result.actual_iterations, solver_runtime_seconds=result.runtime_seconds, phase_timings=result.phase_timings, profile=result.profile, history=[{"iteration": row["iteration"], "destroy": row["destroy"], "repair": row["repair"], "action_id": row["action_id"], "accepted": row["accepted"], "candidate_feasible": row["candidate_feasible"], "best_cost": row["best_cost"]} for row in result.history], first_over_30=FIRST_OVER_30 or "none", first_over_60=FIRST_OVER_60 or "none")
        return 0
    except BaseException as exc:
        emit("run_end", phase="runner", status="exception", exception=repr(exc), first_over_30=FIRST_OVER_30 or "none", first_over_60=FIRST_OVER_60 or "none")
        raise
    finally:
        STACK_STOP.set()
        TRACE_FILE.flush()
        STACK_FILE.flush()
        TRACE_FILE.close()
        STACK_FILE.close()


if __name__ == "__main__":
    exit_code = main()
    # All diagnostic files are flushed and closed in main(). On this Windows
    # runtime, normal interpreter teardown can retain the very large profiling
    # graph after run_end. A direct process exit prevents that probe-only
    # teardown stall without changing any solver call, result, or RNG event.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
