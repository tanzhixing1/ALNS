from __future__ import annotations

import copy
import functools
import hashlib
import json
import statistics
import sys
import threading
import time
import tracemalloc
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

import numpy as np


HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

import alns_profile
import alns_solver
import feasibility as feasibility_module
import objective as objective_module
import operators
from config import build_config
from dataset_loader import generate_toy_data
from initial_solution import initial_solution


OUTPUT = HERE / "raw" / "stage2g0_measurements.json"


def safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [safe(item) for item in value]
    return repr(value)


def digest(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def state_fingerprint(state: Any) -> str:
    return digest(state.cache_signature())


def rng_from_state(saved_state: dict[str, Any]) -> np.random.Generator:
    rng = np.random.default_rng()
    rng.bit_generator.state = copy.deepcopy(saved_state)
    return rng


class MemorySampler:
    def __init__(self) -> None:
        self.peak_working_set = 0
        self.peak_private = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
            wintypes.DWORD,
        ]
        get_memory.restype = wintypes.BOOL
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        process = ctypes.windll.kernel32.GetCurrentProcess()
        while not self._stop.wait(0.02):
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(counters)
            if get_memory(process, ctypes.byref(counters), counters.cb):
                self.peak_working_set = max(
                    self.peak_working_set, int(counters.WorkingSetSize)
                )
                self.peak_private = max(
                    self.peak_private, int(counters.PrivateUsage)
                )

    def __enter__(self) -> "MemorySampler":
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._stop.set()
        self._thread.join()


def semantic_trace(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "round",
        "state_revision",
        "customer_id",
        "raw_candidate_count",
        "unique_candidate_count",
        "van_candidate_count",
        "drone_candidate_count",
        "best_move_identity",
        "best_delta",
        "second_move_identity",
        "second_delta",
        "regret",
        "single_candidate",
        "customer_priority_key",
        "selected_customer",
        "selected",
    )
    return [{key: safe(row.get(key)) for key in keys} for row in rows]


def oracle_result(
    repaired: Any,
    rng: np.random.Generator,
    data: Any,
    config: Any,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    total, breakdown = objective_module.objective(repaired, data, config)
    feasible, violations = feasibility_module.check_solution_feasible(
        repaired, data, config
    )
    return {
        "fingerprint": state_fingerprint(repaired),
        "objective": float(total),
        "checker": bool(feasible),
        "violations": list(violations),
        "rng_state": safe(rng.bit_generator.state),
        "trace": semantic_trace(trace),
        "candidate_count": sum(int(row["raw_candidate_count"]) for row in trace),
        "unique_candidate_count": sum(
            int(row["unique_candidate_count"]) for row in trace
        ),
        "first_best": [safe(row["best_move_identity"]) for row in trace],
        "second_best": [safe(row["second_move_identity"]) for row in trace],
        "regrets": [row["regret"] for row in trace],
        "selected_customers": [
            int(row["customer_id"]) for row in trace if row.get("selected")
        ],
        "selected_moves": [
            safe(row["best_move_identity"]) for row in trace if row.get("selected")
        ],
        "breakdown": safe(breakdown),
    }


def profile_volume(profile: dict[str, Any]) -> dict[str, Any]:
    repair = profile.get("repair", {}).get("regret_repair", {})
    local = profile.get("local_feasibility_cache", {})
    return {
        "raw": int(repair.get("candidate_count", 0)),
        "van_raw": int(repair.get("van_candidate_count", 0)),
        "drone_raw": int(repair.get("drone_candidate_count", 0)),
        "hard_feasible": int(repair.get("feasible_candidate_count", 0)),
        "van_hard_feasible": int(repair.get("van_feasible_candidate_count", 0)),
        "drone_hard_feasible": int(repair.get("drone_feasible_candidate_count", 0)),
        "prefilter_rejected": int(repair.get("candidate_count", 0))
        - int(repair.get("feasible_candidate_count", 0)),
        "local_drone_generated": int(local.get("raw_drone_candidate_count", 0)),
        "local_drone_duplicates": int(local.get("duplicate_candidates_skipped", 0)),
        "objective_calls": int(profile.get("objective_calls", 0)),
        "objective_cache_hits": int(profile.get("objective_cache_hits", 0)),
        "checker_calls": int(profile.get("check_solution_feasible_calls", 0)),
        "checker_cache_hits": int(
            profile.get("check_solution_feasible_cache_hits", 0)
        ),
        "timing_calls": int(profile.get("compute_timing_calls", 0)),
        "timing_cache_hits": int(profile.get("compute_timing_cache_hits", 0)),
        "state_copy_calls": int(profile.get("state_copy_calls", 0)),
        "state_signature_calls": int(profile.get("state_signature_calls", 0)),
        "state_signature_time": float(
            profile.get("state_signature_time_total", 0.0)
        ),
        "repair_rejections": safe(profile.get("repair_rejections", {})),
    }


class DetailedTimer:
    def __init__(self) -> None:
        self.stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "inclusive_seconds": 0.0,
                "exclusive_seconds": 0.0,
                "durations": [],
            }
        )
        self.stack: list[dict[str, float]] = []
        self.patches: list[tuple[Any, str, Any]] = []
        self.score_depth = 0
        self.dedup_depth = 0
        self.eval_context: list[dict[str, Any]] = []
        self.last_signature: dict[int, Any] = {}
        self.move_identity_hashes: list[str] = []
        self.business_state_hashes: list[str] = []
        self.evaluation_identity_hashes: list[str] = []
        self.base_business_state_hashes: list[str] = []
        self.candidate_business_state_hashes: list[str] = []
        self.candidate_evaluation_identity_hashes: list[str] = []
        self.score_objective_counts: list[int] = []
        self.objective_results: list[float] = []
        self.copy_durations: list[float] = []
        self.customer_durations: list[float] = []
        self.raw_dedup_inputs = 0
        self.unique_dedup_outputs = 0

    def _enter(self) -> tuple[float, dict[str, float]]:
        frame = {"child": 0.0}
        self.stack.append(frame)
        return time.perf_counter(), frame

    def _exit(self, name: str, started: float, frame: dict[str, float]) -> float:
        duration = time.perf_counter() - started
        popped = self.stack.pop()
        assert popped is frame
        exclusive = max(0.0, duration - frame["child"])
        row = self.stats[name]
        row["calls"] += 1
        row["inclusive_seconds"] += duration
        row["exclusive_seconds"] += exclusive
        row["durations"].append(duration)
        if self.stack:
            self.stack[-1]["child"] += duration
        return duration

    def patch(self, owner: Any, name: str, wrapped: Any) -> None:
        original = getattr(owner, name)
        self.patches.append((owner, name, original))
        setattr(owner, name, wrapped)

    def timed_patch(self, owner: Any, attr: str, label: str) -> None:
        original = getattr(owner, attr)

        @functools.wraps(original)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            try:
                return original(*args, **kwargs)
            finally:
                duration = self._exit(label, started, frame)
                if label == "State.copy":
                    self.copy_durations.append(duration)
                if label == "customer_evaluation":
                    self.customer_durations.append(duration)

        self.patch(owner, attr, wrapped)

    def install(self, state_type: type) -> None:
        self.timed_patch(state_type, "copy", "State.copy")
        self.timed_patch(state_type, "cache_signature", "state_signature")
        self.timed_patch(
            operators, "_enumerate_feasible_van_moves", "van_enumeration"
        )
        self.timed_patch(
            operators, "_enumerate_feasible_drone_moves", "drone_enumeration"
        )
        self.timed_patch(
            operators, "_van_insert_hard_feasible", "van_hard_prefilter"
        )
        self.timed_patch(
            operators, "_drone_insert_hard_feasible", "drone_hard_prefilter"
        )
        self.timed_patch(
            operators, "_regret_move_order_key", "sorting_tie_key"
        )
        self.timed_patch(
            operators, "_evaluate_regret_customer", "customer_evaluation"
        )

        original_signature = state_type.cache_signature
        # timed_patch already installed a wrapper; decorate that wrapper to capture
        # the exact signatures production requested, without another traversal.
        timed_signature = getattr(state_type, "cache_signature")
        self.patches.pop()
        setattr(state_type, "cache_signature", original_signature)

        @functools.wraps(timed_signature)
        def captured_signature(state: Any) -> Any:
            result = timed_signature(state)
            self.last_signature[id(state)] = result
            if self.eval_context:
                context = self.eval_context[-1]
                if context["state_id"] == id(state):
                    if context["first"] is None:
                        context["first"] = result
                    context["last"] = result
            return result

        self.patch(state_type, "cache_signature", captured_signature)

        original_identity = operators._regret_move_identity

        @functools.wraps(original_identity)
        def identity(*args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            try:
                result = original_identity(*args, **kwargs)
                if self.dedup_depth:
                    self.move_identity_hashes.append(digest(result))
                return result
            finally:
                self._exit("move_identity", started, frame)

        self.patch(operators, "_regret_move_identity", identity)

        original_dedup = operators._deduplicate_regret_moves

        @functools.wraps(original_dedup)
        def dedup(customer: int, moves: list[Any], state: Any) -> list[Any]:
            started, frame = self._enter()
            self.raw_dedup_inputs += len(moves)
            self.dedup_depth += 1
            try:
                result = original_dedup(customer, moves, state)
                self.unique_dedup_outputs += len(result)
                return result
            finally:
                self.dedup_depth -= 1
                self._exit("deduplication", started, frame)

        self.patch(operators, "_deduplicate_regret_moves", dedup)

        original_apply = operators._apply_move

        @functools.wraps(original_apply)
        def apply_move(*args: Any, **kwargs: Any) -> Any:
            label = "candidate_application" if self.score_depth else "selected_commit"
            started, frame = self._enter()
            try:
                return original_apply(*args, **kwargs)
            finally:
                self._exit(label, started, frame)

        self.patch(operators, "_apply_move", apply_move)

        original_score = operators._score_regret_moves_with_exact_objective_delta

        @functools.wraps(original_score)
        def score(*args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            self.score_depth += 1
            self.score_objective_counts.append(0)
            try:
                return original_score(*args, **kwargs)
            finally:
                self.score_objective_counts.pop()
                self.score_depth -= 1
                self._exit("exact_scoring", started, frame)

        self.patch(operators, "_score_regret_moves_with_exact_objective_delta", score)

        original_objective = objective_module.objective

        @functools.wraps(original_objective)
        def objective(state: Any, *args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            context = {"state_id": id(state), "first": None, "last": None}
            self.eval_context.append(context)
            try:
                result = original_objective(state, *args, **kwargs)
                if self.score_depth:
                    is_candidate = self.score_objective_counts[-1] > 0
                    self.score_objective_counts[-1] += 1
                    if context["first"] is not None:
                        self.business_state_hashes.append(digest(context["first"]))
                        target = (
                            self.candidate_business_state_hashes
                            if is_candidate
                            else self.base_business_state_hashes
                        )
                        target.append(digest(context["first"]))
                    if context["last"] is not None:
                        self.evaluation_identity_hashes.append(digest(context["last"]))
                        if is_candidate:
                            self.candidate_evaluation_identity_hashes.append(
                                digest(context["last"])
                            )
                    self.objective_results.append(float(result[0]))
                return result
            finally:
                self.eval_context.pop()
                self._exit("objective", started, frame)

        self.patch(objective_module, "objective", objective)
        self.patch(operators, "objective", objective)

        original_checker = feasibility_module.check_solution_feasible

        @functools.wraps(original_checker)
        def checker(*args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            try:
                return original_checker(*args, **kwargs)
            finally:
                self._exit("canonical_checker", started, frame)

        self.patch(feasibility_module, "check_solution_feasible", checker)
        self.patch(objective_module, "check_solution_feasible", checker)
        self.patch(operators, "check_solution_feasible", checker)

        original_timing = feasibility_module.compute_timing

        @functools.wraps(original_timing)
        def timing(*args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            try:
                return original_timing(*args, **kwargs)
            finally:
                self._exit("compute_timing", started, frame)

        self.patch(feasibility_module, "compute_timing", timing)

        original_waiting = objective_module.compute_waiting_minutes

        @functools.wraps(original_waiting)
        def waiting(*args: Any, **kwargs: Any) -> Any:
            started, frame = self._enter()
            try:
                return original_waiting(*args, **kwargs)
            finally:
                self._exit("compute_waiting", started, frame)

        self.patch(objective_module, "compute_waiting_minutes", waiting)

    def restore(self) -> None:
        for owner, name, original in reversed(self.patches):
            setattr(owner, name, original)
        self.patches.clear()

    def summary(self) -> dict[str, Any]:
        rows = {}
        for name, row in self.stats.items():
            durations = row["durations"]
            rows[name] = {
                "calls": int(row["calls"]),
                "inclusive_seconds": float(row["inclusive_seconds"]),
                "exclusive_seconds": float(row["exclusive_seconds"]),
                "p50_seconds": statistics.median(durations) if durations else 0.0,
                "p90_seconds": percentile(durations, 90),
                "p95_seconds": percentile(durations, 95),
                "p99_seconds": percentile(durations, 99),
            }
        return rows


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent / 100.0
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    fraction = index - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def capture_heavy_fixture() -> tuple[Any, dict[str, Any], Any, Any, dict[str, Any]]:
    config = build_config(
        num_orders=20,
        num_customers=20,
        num_containers=2,
        num_transshipments=2,
        iterations=10,
        seed=42,
        operator_mode="paper_mode",
    )
    data = generate_toy_data(config)
    original = operators.REPAIR_OPERATORS["regret_repair"]
    captured: dict[str, Any] = {}
    calls = 0

    class Captured(RuntimeError):
        pass

    @functools.wraps(original)
    def capture(state: Any, rng: Any, data_arg: Any, config_arg: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            captured["state"] = state.copy()
            captured["rng_state"] = copy.deepcopy(rng.bit_generator.state)
            captured["input_fingerprint"] = state_fingerprint(captured["state"])
            raise Captured("heavy fixture captured")
        return original(state, rng, data_arg, config_arg, *args, **kwargs)

    operators.REPAIR_OPERATORS["regret_repair"] = capture
    prefix_started = time.perf_counter()
    try:
        alns_solver.run_c_alns(data, config)
    except Captured:
        pass
    finally:
        operators.REPAIR_OPERATORS["regret_repair"] = original
        setattr(config.alns, "_inside_alns_loop", False)
    if "state" not in captured:
        raise RuntimeError("current-baseline deterministic second Regret call not captured")
    fixture = {
        "source": "second regret_repair entry in deterministic 20-customer, 2-container, 10-iteration paper-mode prefix",
        "capture_seconds": time.perf_counter() - prefix_started,
        "input_fingerprint": captured["input_fingerprint"],
        "unassigned": list(captured["state"].unassigned),
        "van_count": len(captured["state"].van_routes),
        "drone_count": len(captured["state"].drone_initial_carrier),
        "container_count": len(captured["state"].container_routes),
        "van_routes": safe(captured["state"].van_routes),
        "drone_sorties": safe(captured["state"].drone_sorties),
        "seed": 42,
        "config": {
            "customers": 20,
            "orders": 20,
            "containers": 2,
            "transshipments": 2,
            "operator_mode": "paper_mode",
        },
        "entry": "operators.REPAIR_OPERATORS['regret_repair'] / regret_repair",
    }
    return captured["state"], captured["rng_state"], data, config, fixture


def run_regret_variant(
    fixture_state: Any,
    saved_rng_state: dict[str, Any],
    data: Any,
    config: Any,
    *,
    detailed: bool,
) -> tuple[dict[str, Any], Any]:
    state = fixture_state.copy()
    rng = rng_from_state(saved_rng_state)
    trace: list[dict[str, Any]] = []
    timer = DetailedTimer() if detailed else None
    alns_profile.reset_profile()
    if timer is not None:
        timer.install(type(state))
    try:
        with MemorySampler() as memory:
            started = time.perf_counter()
            repaired = operators.regret_repair(
                state, rng, data, config, trace_collector=trace.append
            )
            wall = time.perf_counter() - started
        profile = alns_profile.snapshot_profile()
    finally:
        if timer is not None:
            timer.restore()
    oracle = oracle_result(repaired, rng, data, config, trace)
    payload: dict[str, Any] = {
        "wall_seconds": wall,
        "peak_working_set_bytes": memory.peak_working_set,
        "peak_private_bytes": memory.peak_private,
        "profile": profile_volume(profile),
        "oracle": oracle,
    }
    if timer is not None:
        business_candidates = timer.candidate_business_state_hashes
        evaluation_candidates = timer.candidate_evaluation_identity_hashes
        payload["timings"] = timer.summary()
        payload["identity"] = {
            "raw_move_identities": timer.raw_dedup_inputs,
            "unique_move_records_after_dedup": timer.unique_dedup_outputs,
            "unique_move_identities": len(set(timer.move_identity_hashes)),
            "candidate_business_states": len(business_candidates),
            "unique_business_states": len(set(business_candidates)),
            "evaluation_identities": len(evaluation_candidates),
            "unique_evaluation_identities": len(set(evaluation_candidates)),
            "duplicate_business_states": len(business_candidates)
            - len(set(business_candidates)),
            "base_objective_evaluations": len(timer.base_business_state_hashes),
            "unique_base_business_states": len(set(timer.base_business_state_hashes)),
        }
        payload["copy_distribution"] = {
            "calls": len(timer.copy_durations),
            "total_seconds": sum(timer.copy_durations),
            "average_seconds": statistics.mean(timer.copy_durations)
            if timer.copy_durations
            else 0.0,
            "p50_seconds": percentile(timer.copy_durations, 50),
            "p90_seconds": percentile(timer.copy_durations, 90),
            "p95_seconds": percentile(timer.copy_durations, 95),
            "p99_seconds": percentile(timer.copy_durations, 99),
        }
        payload["customer_distribution"] = {
            "calls": len(timer.customer_durations),
            "p50_seconds": percentile(timer.customer_durations, 50),
            "p90_seconds": percentile(timer.customer_durations, 90),
            "p95_seconds": percentile(timer.customer_durations, 95),
            "p99_seconds": percentile(timer.customer_durations, 99),
        }
    return payload, repaired


def measure_copy_allocations(state: Any, repetitions: int = 24) -> dict[str, Any]:
    alns_profile.reset_profile()
    tracemalloc.start(1)
    tracemalloc.reset_peak()
    started = time.perf_counter()
    copies = [state.copy() for _ in range(repetitions)]
    elapsed = time.perf_counter() - started
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if len(copies) != repetitions:
        raise AssertionError("copy allocation sample incomplete")
    return {
        "repetitions": repetitions,
        "total_seconds": elapsed,
        "average_seconds": elapsed / repetitions,
        "current_bytes": current,
        "peak_bytes": peak,
        "average_retained_bytes_per_copy": current / repetitions,
        "average_peak_bytes_per_copy": peak / repetitions,
    }


def small_fixture() -> tuple[Any, Any, Any, int, str, str]:
    config = build_config(
        num_customers=6,
        num_orders=6,
        num_transshipments=2,
        num_containers=1,
        iterations=1,
        seed=42,
        warehouse_num_vans={3: 2, 4: 2},
        drones_per_van=2,
        operator_mode="paper_mode",
    )
    config.data.high_floor_ratio = 0.0
    data = generate_toy_data(config)
    data.is_high_floor = {customer: False for customer in data.customers}
    state = initial_solution(data, config)
    selected = state.selected_transshipment
    selected_vans = [
        van_id
        for van_id, home in sorted(state.van_home.items())
        if int(home) == int(selected)
    ]
    launch_van, recovery_van = selected_vans[:2]
    recovery_node, drone_customer = data.customers[:2]
    remaining = [
        customer
        for customer in data.customers
        if customer not in {recovery_node, drone_customer}
    ]
    state.van_routes = {
        launch_van: [selected, *remaining, selected],
        recovery_van: [selected, recovery_node, selected],
    }
    state.sync_primary_van_route()
    state.drone_sorties = []
    state.service_mode = {customer: "van" for customer in data.customers}
    state.service_mode[drone_customer] = "unassigned"
    state.unassigned = [drone_customer]
    data.drone_distance_matrix[selected, drone_customer] = 1.0
    data.drone_distance_matrix[drone_customer, recovery_node] = 1.0
    data.drone_distance_matrix[drone_customer, selected] = 100.0
    data.drone_distance_matrix[recovery_node, drone_customer] = 100.0
    return config, data, state, drone_customer, launch_van, recovery_van


def projection(state: Any) -> dict[str, Any]:
    breakdown = state.metadata.get("cost_breakdown", {})
    return {
        "selected_transshipment": state.selected_transshipment,
        "truck_route": state.truck_route,
        "tractor_routes": state.tractor_routes,
        "container_routes": state.container_routes,
        "van_routes": state.van_routes,
        "van_route": state.van_route,
        "van_home": state.van_home,
        "drone_initial_carrier": state.drone_initial_carrier,
        "drone_home_warehouse": state.drone_home_warehouse,
        "drone_sorties": state.drone_sorties,
        "order_assignment": state.order_assignment,
        "container_assignment": state.container_assignment,
        "service_mode": state.service_mode,
        "unassigned": state.unassigned,
        "timing": state.timing,
        "cost_breakdown": breakdown,
        "feasible": state.metadata.get("feasible"),
        "violations": state.metadata.get("feasibility_violations", []),
    }


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    rows: dict[str, Any] = {}
    if isinstance(value, dict):
        if not value:
            rows[prefix or "$"] = {}
        for key in sorted(value, key=lambda item: str(item)):
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.update(flatten(value[key], child))
    elif isinstance(value, (list, tuple)):
        if not value:
            rows[prefix or "$"] = []
        for index, item in enumerate(value):
            rows.update(flatten(item, f"{prefix}[{index}]"))
    else:
        rows[prefix or "$"] = safe(value)
    return rows


def diff_projection(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = flatten(before)
    right = flatten(after)
    paths = sorted(
        path for path in set(left) | set(right) if left.get(path) != right.get(path)
    )
    categories = sorted({path.split(".", 1)[0].split("[", 1)[0] for path in paths})
    return {
        "changed_paths": paths,
        "changed_categories": categories,
        "changed_leaf_count": len(paths),
        "total_leaf_count": len(set(left) | set(right)),
        "mutation_ratio": len(paths) / max(1, len(set(left) | set(right))),
    }


def move_identity(customer: int, move: Any, state: Any) -> Any:
    return safe(operators._regret_move_identity(customer, move, state))


def materialize_candidate(
    label: str,
    customer: int,
    move: Any,
    base: Any,
    data: Any,
    config: Any,
    predicted: list[str],
) -> dict[str, Any]:
    base_eval = base.copy()
    objective_module.objective(base_eval, data, config)
    before = projection(base_eval)
    candidate = base.copy()
    operators._apply_move(candidate, customer, operators._copy_move(move))
    total, breakdown = objective_module.objective(candidate, data, config)
    feasible, violations = feasibility_module.check_solution_feasible(
        candidate, data, config
    )
    observed = diff_projection(before, projection(candidate))
    observed_set = set(observed["changed_categories"])
    predicted_set = set(predicted)
    return {
        "label": label,
        "move_identity": move_identity(customer, move, base),
        "mode": move.mode,
        "objective": total,
        "checker": feasible,
        "violations": violations,
        "predicted_categories": sorted(predicted_set),
        "observed": observed,
        "false_negatives": sorted(observed_set - predicted_set),
        "false_positives": sorted(predicted_set - observed_set),
        "cost_breakdown": safe(breakdown),
    }


def move_from_safe_identity(identity: list[Any]) -> Any:
    if identity[0] == "van":
        return operators.InsertionMove(
            mode="van",
            cost=0.0,
            index=int(identity[4]),
            van_id=str(identity[2]),
        )
    sortie = operators._make_drone_sortie(
        int(identity[4]),
        list(identity[11]),
        int(identity[8]),
        drone_id=str(identity[2]),
        launch_van_id=str(identity[3]),
        recovery_van_id=str(identity[7]),
    )
    sortie["launch_position"] = int(identity[5])
    sortie["recovery_position"] = int(identity[9])
    return operators.InsertionMove(mode="drone", cost=0.0, sortie=sortie)


def audit_heavy_linked_candidate(
    state: Any,
    data: Any,
    config: Any,
    selected_move_identities: list[list[Any]],
) -> dict[str, Any]:
    for identity in selected_move_identities[:-1]:
        operators._apply_move(
            state,
            int(identity[1]),
            move_from_safe_identity(identity),
        )
    identity = selected_move_identities[-1]
    return materialize_candidate(
        "linked_multi_customer_relaunch",
        int(identity[1]),
        move_from_safe_identity(identity),
        state,
        data,
        config,
        [
            "drone_sorties",
            "service_mode",
            "unassigned",
            "timing",
            "cost_breakdown",
            "feasible",
            "violations",
            "van_routes",
            "van_route",
        ],
    )


def run_small_audit() -> dict[str, Any]:
    config, data, state, customer, launch_van, recovery_van = small_fixture()
    input_fingerprint = state_fingerprint(state)
    clean, _ = run_regret_variant(
        state,
        copy.deepcopy(np.random.default_rng(2026).bit_generator.state),
        data,
        config,
        detailed=False,
    )
    detailed, _ = run_regret_variant(
        state,
        copy.deepcopy(np.random.default_rng(2026).bit_generator.state),
        data,
        config,
        detailed=True,
    )
    moves, stats = operators._enumerate_regret_moves(customer, state, data, config)
    van_moves = [move for move in moves if move.mode == "van"]
    same_moves = [
        move
        for move in moves
        if move.mode == "drone"
        and move.sortie.get("launch_van_id") == move.sortie.get("recovery_van_id")
    ]
    cross_moves = [
        move
        for move in moves
        if move.mode == "drone"
        and move.sortie.get("launch_van_id") != move.sortie.get("recovery_van_id")
    ]
    multi_moves = [
        move
        for move in moves
        if move.mode == "drone" and len(move.sortie.get("customers", [])) > 1
    ]
    predicted_van = [
        "van_routes",
        "van_route",
        "service_mode",
        "unassigned",
        "timing",
        "cost_breakdown",
        "feasible",
        "violations",
        "drone_sorties",
    ]
    predicted_drone = [
        "drone_sorties",
        "service_mode",
        "unassigned",
        "timing",
        "cost_breakdown",
        "feasible",
        "violations",
        "van_routes",
        "van_route",
    ]
    representatives = []
    if van_moves:
        representatives.append(
            materialize_candidate(
                "van_insertion",
                customer,
                van_moves[0],
                state,
                data,
                config,
                predicted_van,
            )
        )
    if same_moves:
        representatives.append(
            materialize_candidate(
                "same_van_drone",
                customer,
                same_moves[0],
                state,
                data,
                config,
                predicted_drone,
            )
        )
    if cross_moves:
        representatives.append(
            materialize_candidate(
                "cross_van_flexible_docking",
                customer,
                cross_moves[0],
                state,
                data,
                config,
                predicted_drone,
            )
        )
    if multi_moves:
        representatives.append(
            materialize_candidate(
                "linked_or_multi_customer_sortie",
                customer,
                multi_moves[0],
                state,
                data,
                config,
                predicted_drone,
            )
        )

    high_data = copy.deepcopy(data)
    high_data.is_high_floor[customer] = True
    high_moves, _ = operators._enumerate_regret_moves(
        customer, state.copy(), high_data, config
    )
    if high_moves:
        representatives.append(
            materialize_candidate(
                "high_floor_drone_customer",
                customer,
                high_moves[0],
                state,
                high_data,
                config,
                predicted_drone,
            )
        )

    capacity_row = None
    if van_moves:
        capacity_candidates = []
        for move in van_moves:
            route = state.van_routes[move.van_id]
            candidate_route = route[: move.index] + [customer] + route[move.index :]
            payload = operators._route_payload(candidate_route, data)
            capacity_candidates.append((config.fleet.van_capacity_kg - payload, move))
        slack, move = min(capacity_candidates, key=lambda item: item[0])
        boundary_config = copy.deepcopy(config)
        boundary_route = state.van_routes[move.van_id]
        exact_payload = operators._route_payload(
            boundary_route[: move.index]
            + [customer]
            + boundary_route[move.index :],
            data,
        )
        boundary_config.fleet.van_capacity_kg = float(exact_payload)
        boundary_moves, _ = operators._enumerate_regret_moves(
            customer, state.copy(), data, boundary_config
        )
        boundary_move = next(
            candidate
            for candidate in boundary_moves
            if candidate.mode == "van"
            and candidate.van_id == move.van_id
            and candidate.index == move.index
        )
        capacity_row = {
            "original_slack_kg": float(slack),
            "boundary_capacity_kg": float(exact_payload),
            "slack_kg": 0.0,
            "representative": materialize_candidate(
                "capacity_exact_boundary",
                customer,
                boundary_move,
                state,
                data,
                boundary_config,
                predicted_van,
            ),
        }

    time_rows = []
    for move in moves:
        candidate = state.copy()
        operators._apply_move(candidate, customer, operators._copy_move(move))
        objective_module.objective(candidate, data, config)
        served = move.sortie.get("customers", []) if move.mode == "drone" else [customer]
        slacks = []
        for served_customer in served:
            service_start = candidate.timing.get("service_start", {}).get(served_customer)
            latest = data.time_windows.get(served_customer, (0.0, float("inf")))[1]
            if service_start is not None:
                slacks.append(float(latest) - float(service_start))
        if slacks:
            time_rows.append((min(slacks), move))
    time_boundary = None
    if time_rows:
        slack, move = min(time_rows, key=lambda item: item[0])
        boundary_data = copy.deepcopy(data)
        boundary_candidate = state.copy()
        operators._apply_move(
            boundary_candidate, customer, operators._copy_move(move)
        )
        objective_module.objective(boundary_candidate, boundary_data, config)
        boundary_start = float(
            boundary_candidate.timing.get("service_start", {})[customer]
        )
        earliest, _ = boundary_data.time_windows[customer]
        boundary_data.time_windows[customer] = (float(earliest), boundary_start)
        boundary_moves, _ = operators._enumerate_regret_moves(
            customer, state.copy(), boundary_data, config
        )
        target_identity = operators._regret_move_identity(customer, move, state)
        boundary_move = next(
            candidate
            for candidate in boundary_moves
            if operators._regret_move_identity(customer, candidate, state)
            == target_identity
        )
        time_boundary = {
            "original_slack_minutes": float(slack),
            "boundary_latest": boundary_start,
            "slack_minutes": 0.0,
            "representative": materialize_candidate(
                "time_window_exact_boundary",
                customer,
                boundary_move,
                state,
                boundary_data,
                config,
                predicted_drone if move.mode == "drone" else predicted_van,
            ),
        }

    return {
        "fixture": {
            "source": "tests/test_stage2c_regret2.py::_cross_van_case semantics reconstructed without changing tests",
            "input_fingerprint": input_fingerprint,
            "customer": customer,
            "launch_van": launch_van,
            "recovery_van": recovery_van,
            "unassigned": list(state.unassigned),
            "van_routes": safe(state.van_routes),
            "seed": 2026,
            "operator_mode": "paper_mode",
        },
        "clean": clean,
        "instrumented": detailed,
        "enumeration": {
            "stats": safe(stats),
            "move_count": len(moves),
            "van_count": len(van_moves),
            "same_van_drone_count": len(same_moves),
            "cross_van_drone_count": len(cross_moves),
            "multi_customer_drone_count": len(multi_moves),
            "high_floor_move_count": len(high_moves),
        },
        "representatives": representatives,
        "capacity_boundary": capacity_row,
        "time_window_boundary": time_boundary,
    }


def solver_semantics(result: Any, data: Any, config: Any) -> dict[str, Any]:
    total, breakdown = objective_module.objective(result.best_state, data, config)
    feasible, violations = feasibility_module.check_solution_feasible(
        result.best_state, data, config
    )
    history_keys = (
        "iteration",
        "action_id",
        "destroy",
        "repair",
        "accepted",
        "candidate_feasible",
        "current_cost",
        "candidate_cost",
        "best_cost",
        "operator_mode",
        "action_registry_fingerprint",
    )
    return {
        "objective": total,
        "checker": feasible,
        "violations": violations,
        "fingerprint": state_fingerprint(result.best_state),
        "history": [
            {key: safe(row.get(key)) for key in history_keys} for row in result.history
        ],
        "action_history": [int(row["action_id"]) for row in result.history],
        "breakdown": safe(breakdown),
    }


def run_solver_variant(instrumented: bool) -> dict[str, Any]:
    config = build_config(
        num_customers=10,
        num_orders=10,
        num_transshipments=2,
        num_containers=1,
        iterations=5,
        seed=4,
        operator_mode="paper_mode",
    )
    data = generate_toy_data(config)
    original = operators.REPAIR_OPERATORS["regret_repair"]
    durations: list[float] = []

    @functools.wraps(original)
    def timed(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            durations.append(time.perf_counter() - started)

    if instrumented:
        operators.REPAIR_OPERATORS["regret_repair"] = timed
    try:
        with MemorySampler() as memory:
            started = time.perf_counter()
            result = alns_solver.run_c_alns(data, config)
            wall = time.perf_counter() - started
    finally:
        operators.REPAIR_OPERATORS["regret_repair"] = original
    return {
        "wall_seconds": wall,
        "solver_reported_seconds": result.runtime_seconds,
        "alns_loop_seconds": result.phase_timings.get("t_alns_loop", 0.0),
        "regret_calls": len(durations),
        "regret_durations": durations,
        "regret_total_seconds": sum(durations),
        "regret_share_of_solver_wall": sum(durations) / wall if wall else 0.0,
        "regret_p50_seconds": percentile(durations, 50),
        "regret_p90_seconds": percentile(durations, 90),
        "regret_p95_seconds": percentile(durations, 95),
        "peak_working_set_bytes": memory.peak_working_set,
        "peak_private_bytes": memory.peak_private,
        "profile": profile_volume(result.profile),
        "semantics": solver_semantics(result, data, config),
    }


def same_candidate_volume(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = (
        "raw",
        "van_raw",
        "drone_raw",
        "hard_feasible",
        "van_hard_feasible",
        "drone_hard_feasible",
        "prefilter_rejected",
        "local_drone_generated",
        "local_drone_duplicates",
        "state_copy_calls",
        "repair_rejections",
    )
    return all(left.get(key) == right.get(key) for key in keys)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"event": "capture_heavy_start"}), flush=True)
    heavy_state, heavy_rng, heavy_data, heavy_config, heavy_fixture = (
        capture_heavy_fixture()
    )
    print(json.dumps({"event": "heavy_clean_start"}), flush=True)
    heavy_clean, heavy_clean_state = run_regret_variant(
        heavy_state, heavy_rng, heavy_data, heavy_config, detailed=False
    )
    print(
        json.dumps(
            {"event": "heavy_clean_end", "wall_seconds": heavy_clean["wall_seconds"]}
        ),
        flush=True,
    )
    print(json.dumps({"event": "heavy_instrumented_start"}), flush=True)
    heavy_instrumented, _ = run_regret_variant(
        heavy_state, heavy_rng, heavy_data, heavy_config, detailed=True
    )
    print(
        json.dumps(
            {
                "event": "heavy_instrumented_end",
                "wall_seconds": heavy_instrumented["wall_seconds"],
            }
        ),
        flush=True,
    )
    copy_allocations = measure_copy_allocations(heavy_state)
    print(json.dumps({"event": "small_audit_start"}), flush=True)
    small = run_small_audit()
    print(json.dumps({"event": "solver_clean_start"}), flush=True)
    solver_clean = run_solver_variant(False)
    print(json.dumps({"event": "solver_instrumented_start"}), flush=True)
    solver_instrumented = run_solver_variant(True)

    payload = {
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "baseline_commit": "172166eea9e34ae5551302d4bfa1cdb62ebc479b",
        },
        "heavy": {
            "fixture": heavy_fixture,
            "clean": heavy_clean,
            "instrumented": heavy_instrumented,
            "copy_allocations": copy_allocations,
            "retention": {
                "exact_scoring_candidate_copies_retained": 0,
                "exact_scoring_candidate_copies_discarded": heavy_instrumented[
                    "identity"
                ]["candidate_business_states"],
                "selected_move_materialization": "applied in-place to working State; scored candidate copy is not retained",
            },
        },
        "small": small,
        "solver": {
            "fixture": {
                "customers": 10,
                "orders": 10,
                "containers": 1,
                "transshipments": 2,
                "iterations": 5,
                "seed": 4,
                "operator_mode": "paper_mode",
            },
            "clean": solver_clean,
            "instrumented": solver_instrumented,
        },
    }
    payload["neutrality"] = {
        "heavy": heavy_clean["oracle"] == heavy_instrumented["oracle"],
        "heavy_candidate_volume": same_candidate_volume(
            heavy_clean["profile"], heavy_instrumented["profile"]
        ),
        "small": small["clean"]["oracle"] == small["instrumented"]["oracle"],
        "small_candidate_volume": same_candidate_volume(
            small["clean"]["profile"], small["instrumented"]["profile"]
        ),
        "solver": solver_clean["semantics"] == solver_instrumented["semantics"],
        "solver_candidate_volume": same_candidate_volume(
            solver_clean["profile"], solver_instrumented["profile"]
        ),
    }
    OUTPUT.write_text(json.dumps(safe(payload), indent=2), encoding="utf-8")
    print(json.dumps({"event": "complete", "neutrality": payload["neutrality"]}), flush=True)


if __name__ == "__main__":
    main()
