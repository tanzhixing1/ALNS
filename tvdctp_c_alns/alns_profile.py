from __future__ import annotations

import time
from collections import Counter
from copy import deepcopy
from typing import Any, Dict, Optional


_PROFILE: Dict[str, Any] = {}
_CACHE: Dict[str, Dict[tuple[int, object], Any]] = {}
_LOCAL_FEASIBILITY_CACHE: Dict[tuple[object, ...], Any] = {}
_LOCAL_FEASIBILITY_KEY_COUNTS: Counter[tuple[object, ...]] = Counter()
_REPAIR_STACK: list[tuple[str, float]] = []
_PAIR_STACK: list[tuple[str, str, float]] = []


def reset_profile() -> None:
    _PROFILE.clear()
    _PROFILE.update(
        {
            "check_solution_feasible_calls": 0,
            "check_solution_feasible_cache_hits": 0,
            "compute_timing_calls": 0,
            "compute_timing_cache_hits": 0,
            "objective_calls": 0,
            "objective_cache_hits": 0,
            "cache_misses": 0,
            "state_copy_calls": 0,
            "state_deepcopy_calls": 0,
            "state_signature_calls": 0,
            "state_signature_time_total": 0.0,
            "local_feasibility_cache": {
                "enabled": False,
                "raw_drone_candidate_count": 0,
                "unique_drone_candidate_count": 0,
                "duplicate_drone_candidate_count": 0,
                "duplicate_ratio": None,
                "cache_hit_count": 0,
                "cache_miss_count": 0,
                "cache_hit_ratio": None,
                "drone_candidate_eval_time": 0.0,
                "top_duplicated_keys": [],
                "cache_key_fields": [
                    "drone_id",
                    "launch_van",
                    "launch_node",
                    "launch_pos",
                    "recovery_van",
                    "recovery_node",
                    "recovery_pos",
                    "customer_tuple",
                    "relevant_van_route_signature",
                    "existing_drone_sortie_signature",
                    "service_mode_signature",
                    "unassigned_signature",
                    "warehouse_ready_signature",
                    "container_assignment_signature",
                    "container_destination_signature",
                ],
            },
            "repair": {},
            "operator_pairs": {},
            "repair_rejections": {},
            "destroy": {
                "calls": 0,
                "removed_customer_counts": [],
                "removed_high_floor_count": 0,
                "removed_drone_customer_count": 0,
                "removed_van_customer_count": 0,
                "cascade_expansion_counts": [],
            },
        }
    )
    _CACHE.clear()
    _LOCAL_FEASIBILITY_CACHE.clear()
    _LOCAL_FEASIBILITY_KEY_COUNTS.clear()
    _REPAIR_STACK.clear()
    _PAIR_STACK.clear()


def snapshot_profile() -> Dict[str, Any]:
    _sync_local_feasibility_cache_profile()
    return deepcopy(_PROFILE)


def increment(name: str, amount: int = 1) -> None:
    if not _PROFILE:
        reset_profile()
    _PROFILE[name] = int(_PROFILE.get(name, 0)) + int(amount)


def add_value(name: str, amount: float) -> None:
    if not _PROFILE:
        reset_profile()
    _PROFILE[name] = float(_PROFILE.get(name, 0.0)) + float(amount)


def get_cache(namespace: str, state: Any, signature: object) -> Optional[Any]:
    cache = _CACHE.setdefault(namespace, {})
    value = cache.get((id(state), signature))
    if value is None:
        increment("cache_misses")
    return value


def set_cache(namespace: str, state: Any, signature: object, value: Any) -> None:
    cache = _CACHE.setdefault(namespace, {})
    cache[(id(state), signature)] = value


def _local_cache_stats() -> Dict[str, Any]:
    if not _PROFILE:
        reset_profile()
    return _PROFILE.setdefault("local_feasibility_cache", {})


def set_local_feasibility_cache_enabled(enabled: bool) -> None:
    stats = _local_cache_stats()
    stats["enabled"] = bool(enabled)


def get_local_feasibility_cache(
    key: tuple[object, ...], *, enabled: bool
) -> Optional[Any]:
    stats = _local_cache_stats()
    stats["enabled"] = bool(enabled)
    stats["raw_drone_candidate_count"] = int(
        stats.get("raw_drone_candidate_count", 0)
    ) + 1
    _LOCAL_FEASIBILITY_KEY_COUNTS[key] += 1
    if enabled and key in _LOCAL_FEASIBILITY_CACHE:
        stats["cache_hit_count"] = int(stats.get("cache_hit_count", 0)) + 1
        return _LOCAL_FEASIBILITY_CACHE[key]
    stats["cache_miss_count"] = int(stats.get("cache_miss_count", 0)) + 1
    return None


def set_local_feasibility_cache(
    key: tuple[object, ...], value: Any, *, enabled: bool
) -> None:
    if enabled:
        _LOCAL_FEASIBILITY_CACHE[key] = value


def add_local_feasibility_eval_time(amount: float) -> None:
    stats = _local_cache_stats()
    stats["drone_candidate_eval_time"] = float(
        stats.get("drone_candidate_eval_time", 0.0)
    ) + float(amount)


def _sync_local_feasibility_cache_profile() -> None:
    if not _PROFILE:
        reset_profile()
    stats = _local_cache_stats()
    raw = int(stats.get("raw_drone_candidate_count", 0))
    unique = len(_LOCAL_FEASIBILITY_KEY_COUNTS)
    duplicate = max(0, raw - unique)
    hits = int(stats.get("cache_hit_count", 0))
    misses = int(stats.get("cache_miss_count", 0))
    stats["unique_drone_candidate_count"] = unique
    stats["duplicate_drone_candidate_count"] = duplicate
    stats["duplicate_ratio"] = duplicate / raw if raw else None
    stats["cache_hit_ratio"] = hits / (hits + misses) if hits + misses else None
    stats["top_duplicated_keys"] = [
        {"candidate_key": repr(key), "count": int(count)}
        for key, count in _LOCAL_FEASIBILITY_KEY_COUNTS.most_common(10)
    ]


def _repair_stats(name: str) -> Dict[str, Any]:
    if not _PROFILE:
        reset_profile()
    repair = _PROFILE.setdefault("repair", {})
    return repair.setdefault(
        name,
        {
            "calls": 0,
            "time_seconds": 0.0,
            "candidate_count": 0,
            "feasible_candidate_count": 0,
            "van_candidate_count": 0,
            "van_feasible_candidate_count": 0,
            "drone_candidate_count": 0,
            "drone_feasible_candidate_count": 0,
        },
    )


def enter_repair(name: str) -> None:
    stats = _repair_stats(name)
    stats["calls"] = int(stats["calls"]) + 1
    _REPAIR_STACK.append((name, time.perf_counter()))


def exit_repair(name: str) -> None:
    if not _REPAIR_STACK:
        return
    active_name, start = _REPAIR_STACK.pop()
    stats = _repair_stats(active_name)
    stats["time_seconds"] = float(stats["time_seconds"]) + (
        time.perf_counter() - start
    )


def active_repair_name() -> str:
    return _REPAIR_STACK[-1][0] if _REPAIR_STACK else "unscoped"


def _pair_key(destroy_name: str, repair_name: str) -> str:
    return f"{destroy_name}::{repair_name}"


def _pair_stats(destroy_name: str, repair_name: str) -> Dict[str, Any]:
    if not _PROFILE:
        reset_profile()
    pairs = _PROFILE.setdefault("operator_pairs", {})
    return pairs.setdefault(
        _pair_key(destroy_name, repair_name),
        {
            "destroy_operator": destroy_name,
            "repair_operator": repair_name,
            "calls": 0,
            "generated_candidates": 0,
            "local_feasible_candidates": 0,
            "full_feasible_candidates": 0,
            "accepted_candidates": 0,
            "improved_candidates": 0,
            "total_runtime": 0.0,
            "best_improvement_contributed": 0.0,
            "delta_cost_sum": 0.0,
            "selected_weight_start": None,
            "selected_weight_end": None,
        },
    )


def enter_operator_pair(destroy_name: str, repair_name: str) -> None:
    stats = _pair_stats(destroy_name, repair_name)
    stats["calls"] = int(stats["calls"]) + 1
    _PAIR_STACK.append((destroy_name, repair_name, time.perf_counter()))


def exit_operator_pair(
    destroy_name: str,
    repair_name: str,
    *,
    candidate_feasible: bool,
    accepted: bool,
    improved: bool,
    delta_cost: float,
    best_improvement: float,
    selected_weight_start: float,
    selected_weight_end: float,
) -> None:
    start = time.perf_counter()
    if _PAIR_STACK:
        active_destroy, active_repair, start = _PAIR_STACK.pop()
        destroy_name = active_destroy
        repair_name = active_repair
    stats = _pair_stats(destroy_name, repair_name)
    stats["total_runtime"] = float(stats["total_runtime"]) + (
        time.perf_counter() - start
    )
    stats["generated_candidates"] = int(stats["generated_candidates"]) + 1
    if candidate_feasible:
        stats["full_feasible_candidates"] = int(stats["full_feasible_candidates"]) + 1
    if accepted:
        stats["accepted_candidates"] = int(stats["accepted_candidates"]) + 1
    if improved:
        stats["improved_candidates"] = int(stats["improved_candidates"]) + 1
    stats["delta_cost_sum"] = float(stats["delta_cost_sum"]) + float(delta_cost)
    stats["best_improvement_contributed"] = max(
        float(stats["best_improvement_contributed"]), float(best_improvement)
    )
    if stats["selected_weight_start"] is None:
        stats["selected_weight_start"] = float(selected_weight_start)
    stats["selected_weight_end"] = float(selected_weight_end)


def record_repair_candidate(kind: str, feasible: bool) -> None:
    stats = _repair_stats(active_repair_name())
    stats["candidate_count"] = int(stats["candidate_count"]) + 1
    stats[f"{kind}_candidate_count"] = int(stats[f"{kind}_candidate_count"]) + 1
    if _PAIR_STACK:
        pair_stats = _pair_stats(_PAIR_STACK[-1][0], _PAIR_STACK[-1][1])
        if feasible:
            pair_stats["local_feasible_candidates"] = (
                int(pair_stats["local_feasible_candidates"]) + 1
            )
    if feasible:
        stats["feasible_candidate_count"] = int(stats["feasible_candidate_count"]) + 1
        stats[f"{kind}_feasible_candidate_count"] = (
            int(stats[f"{kind}_feasible_candidate_count"]) + 1
        )


def record_repair_rejection(reason: str) -> None:
    if not _PROFILE:
        reset_profile()
    rejections = _PROFILE.setdefault("repair_rejections", {})
    rejections[reason] = int(rejections.get(reason, 0)) + 1


def record_destroy_result(
    *,
    removed_customers: list[int],
    high_floor_customers: list[int],
    drone_customers: list[int],
    van_customers: list[int],
    cascade_expansion_count: int = 0,
) -> None:
    if not _PROFILE:
        reset_profile()
    stats = _PROFILE.setdefault("destroy", {})
    stats["calls"] = int(stats.get("calls", 0)) + 1
    stats.setdefault("removed_customer_counts", []).append(len(removed_customers))
    stats["removed_high_floor_count"] = int(stats.get("removed_high_floor_count", 0)) + len(
        high_floor_customers
    )
    stats["removed_drone_customer_count"] = int(
        stats.get("removed_drone_customer_count", 0)
    ) + len(drone_customers)
    stats["removed_van_customer_count"] = int(
        stats.get("removed_van_customer_count", 0)
    ) + len(van_customers)
    stats.setdefault("cascade_expansion_counts", []).append(int(cascade_expansion_count))
