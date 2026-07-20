from __future__ import annotations

import copy
import functools
import gc
import hashlib
import json
import statistics
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import numpy as np


PACKAGE_DIR = Path(__file__).resolve().parents[2]
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import alns_profile
import alns_solver
import objective as objective_module
import operators
from config import build_config
from dataset_loader import generate_toy_data


OUTPUT = Path(__file__).with_name("preimplementation_duplicate_audit.json")


def fingerprint(state) -> str:
    return hashlib.sha256(repr(state.cache_signature()).encode("utf-8")).hexdigest()


def rng_from_state(saved_state):
    rng = np.random.default_rng()
    rng.bit_generator.state = copy.deepcopy(saved_state)
    return rng


def compact_key(value) -> bytes:
    return hashlib.sha256(repr(value).encode("utf-8")).digest()


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
        while not self._stop.wait(0.05):
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(counters)
            if get_memory(process, ctypes.byref(counters), counters.cb):
                self.peak_working_set = max(
                    self.peak_working_set, int(counters.WorkingSetSize)
                )
                self.peak_private = max(
                    self.peak_private, int(counters.PrivateUsage)
                )

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        self._thread.join()


def main() -> None:
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
    original_regret = operators.REPAIR_OPERATORS["regret_repair"]
    captured = {}
    regret_call_durations = []
    regret_call_count = 0

    @functools.wraps(original_regret)
    def capture_regret(state, rng, data_arg, config_arg, *args, **kwargs):
        nonlocal regret_call_count
        regret_call_count += 1
        if regret_call_count == 2:
            captured["state"] = state.copy()
            captured["rng_state"] = copy.deepcopy(rng.bit_generator.state)
        started = time.perf_counter()
        result = original_regret(state, rng, data_arg, config_arg, *args, **kwargs)
        regret_call_durations.append(time.perf_counter() - started)
        return result

    operators.REPAIR_OPERATORS["regret_repair"] = capture_regret
    try:
        result = alns_solver.run_c_alns(data, config)
    finally:
        operators.REPAIR_OPERATORS["regret_repair"] = original_regret

    if "state" not in captured:
        raise RuntimeError("the deterministic second regret call was not captured")

    clean_runs = []
    for repetition in range(1, 4):
        gc.collect()
        alns_profile.reset_profile()
        with MemorySampler() as memory:
            started = time.perf_counter()
            repaired = original_regret(
                captured["state"].copy(),
                rng_from_state(captured["rng_state"]),
                data,
                config,
            )
            elapsed = time.perf_counter() - started
        profile = alns_profile._PROFILE
        clean_runs.append(
            {
                "repetition": repetition,
                "wall_seconds": elapsed,
                "result_fingerprint": fingerprint(repaired),
                "objective_calls": int(profile["objective_calls"]),
                "checker_calls": int(profile["check_solution_feasible_calls"]),
                "state_copy_calls": int(profile["state_copy_calls"]),
                "peak_working_set_bytes": memory.peak_working_set,
                "peak_private_bytes": memory.peak_private,
            }
        )
        print(json.dumps({"event": "clean_replay", **clean_runs[-1]}), flush=True)

    audit = {
        "objective_keys": [],
        "checker_keys": [],
        "candidate_keys": [],
        "base_keys": [],
        "candidate_identities": [],
        "raw_candidate_records": 0,
        "unique_candidate_identities": 0,
        "copy_calls": 0,
        "copy_seconds": 0.0,
        "score_active": False,
        "objective_index": 0,
    }
    original_operator_objective = operators.objective
    original_checker = objective_module.check_solution_feasible
    original_score = operators._score_regret_moves_with_exact_objective_delta
    original_dedup = operators._deduplicate_regret_moves
    state_type = type(captured["state"])
    original_copy = state_type.copy

    @functools.wraps(original_operator_objective)
    def audited_objective(state, data_arg, config_arg):
        if audit["score_active"]:
            key = compact_key(state.cache_signature())
            audit["objective_keys"].append(key)
            if audit["objective_index"] == 0:
                audit["base_keys"].append(key)
            else:
                audit["candidate_keys"].append(key)
            audit["objective_index"] += 1
        return original_operator_objective(state, data_arg, config_arg)

    @functools.wraps(original_checker)
    def audited_checker(state, data_arg, config_arg):
        audit["checker_keys"].append(compact_key(state.cache_signature()))
        return original_checker(state, data_arg, config_arg)

    @functools.wraps(original_score)
    def audited_score(customer, moves, state, data_arg, config_arg):
        audit["score_active"] = True
        audit["objective_index"] = 0
        audit["candidate_identities"].extend(
            compact_key(operators._regret_move_identity(customer, move, state))
            for move in moves
        )
        try:
            return original_score(customer, moves, state, data_arg, config_arg)
        finally:
            audit["score_active"] = False

    @functools.wraps(original_dedup)
    def audited_dedup(customer, moves, state):
        identities = [
            operators._regret_move_identity(customer, move, state) for move in moves
        ]
        audit["raw_candidate_records"] += len(identities)
        audit["unique_candidate_identities"] += len(set(identities))
        return original_dedup(customer, moves, state)

    @functools.wraps(original_copy)
    def audited_copy(state):
        started = time.perf_counter()
        result = original_copy(state)
        audit["copy_calls"] += 1
        audit["copy_seconds"] += time.perf_counter() - started
        return result

    operators.objective = audited_objective
    objective_module.check_solution_feasible = audited_checker
    operators._score_regret_moves_with_exact_objective_delta = audited_score
    operators._deduplicate_regret_moves = audited_dedup
    state_type.copy = audited_copy
    gc.collect()
    alns_profile.reset_profile()
    audit_started = time.perf_counter()
    try:
        with MemorySampler() as audit_memory:
            audited_result = original_regret(
                captured["state"].copy(),
                rng_from_state(captured["rng_state"]),
                data,
                config,
            )
            audit_seconds = time.perf_counter() - audit_started
    finally:
        operators.objective = original_operator_objective
        objective_module.check_solution_feasible = original_checker
        operators._score_regret_moves_with_exact_objective_delta = original_score
        operators._deduplicate_regret_moves = original_dedup
        state_type.copy = original_copy

    def duplicate_count(items) -> int:
        return sum(count - 1 for count in Counter(items).values())

    result_payload = {
        "config": {
            "num_customers": 20,
            "num_containers": 2,
            "iterations": 10,
            "seed": 42,
            "operator_mode": "paper_mode",
        },
        "prefix_history": result.history,
        "prefix_solver_seconds": result.runtime_seconds,
        "regret_call_durations": regret_call_durations,
        "focused_clean_runs": clean_runs,
        "focused_clean_median_seconds": statistics.median(
            item["wall_seconds"] for item in clean_runs
        ),
        "focused_result_fingerprint": clean_runs[0]["result_fingerprint"],
        "audit_replay_seconds": audit_seconds,
        "audit_result_fingerprint": fingerprint(audited_result),
        "raw_candidate_records": audit["raw_candidate_records"],
        "unique_candidate_identities": audit["unique_candidate_identities"],
        "duplicate_candidate_records": (
            audit["raw_candidate_records"] - audit["unique_candidate_identities"]
        ),
        "scored_candidate_records": len(audit["candidate_identities"]),
        "duplicate_scored_candidate_identities": duplicate_count(
            audit["candidate_identities"]
        ),
        "candidate_business_states": len(audit["candidate_keys"]),
        "unique_candidate_business_states": len(set(audit["candidate_keys"])),
        "duplicate_final_states": duplicate_count(audit["candidate_keys"]),
        "objective_evaluations": len(audit["objective_keys"]),
        "duplicate_objective_evaluations": duplicate_count(audit["objective_keys"]),
        "checker_evaluations": len(audit["checker_keys"]),
        "duplicate_checker_evaluations": duplicate_count(audit["checker_keys"]),
        "duplicate_base_objective_evaluations": duplicate_count(audit["base_keys"]),
        "state_copy_calls": audit["copy_calls"],
        "state_copy_seconds": audit["copy_seconds"],
        "unselected_candidate_state_count": len(audit["candidate_keys"]),
        "audit_peak_working_set_bytes": audit_memory.peak_working_set,
        "audit_peak_private_bytes": audit_memory.peak_private,
    }
    OUTPUT.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    print(json.dumps({"event": "audit_complete", **result_payload}, default=str), flush=True)


if __name__ == "__main__":
    main()
