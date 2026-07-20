from __future__ import annotations

import copy
import functools
import gc
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np


PACKAGE_DIR = Path(__file__).resolve().parents[2]
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import alns_profile
import alns_solver
import operators
from config import build_config
from dataset_loader import generate_toy_data
from stage2e2_audit_probe import MemorySampler, fingerprint


OUTPUT = Path(__file__).with_name("optimized_focused_runs.json")


def rng_from_state(saved_state):
    rng = np.random.default_rng()
    rng.bit_generator.state = copy.deepcopy(saved_state)
    return rng


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
    optimized_regret = operators.REPAIR_OPERATORS["regret_repair"]
    captured = {}
    call_durations = []
    call_count = 0

    @functools.wraps(optimized_regret)
    def capture_regret(state, rng, data_arg, config_arg, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            captured["state"] = state.copy()
            captured["rng_state"] = copy.deepcopy(rng.bit_generator.state)
        started = time.perf_counter()
        result = optimized_regret(state, rng, data_arg, config_arg, *args, **kwargs)
        call_durations.append(time.perf_counter() - started)
        return result

    operators.REPAIR_OPERATORS["regret_repair"] = capture_regret
    try:
        with MemorySampler() as prefix_memory:
            result = alns_solver.run_c_alns(data, config)
    finally:
        operators.REPAIR_OPERATORS["regret_repair"] = optimized_regret

    runs = []
    for repetition in range(1, 4):
        gc.collect()
        alns_profile.reset_profile()
        with MemorySampler() as memory:
            started = time.perf_counter()
            repaired = optimized_regret(
                captured["state"].copy(),
                rng_from_state(captured["rng_state"]),
                data,
                config,
            )
            elapsed = time.perf_counter() - started
        profile = alns_profile._PROFILE
        cache = dict(profile["regret_exact_cache"])
        runs.append(
            {
                "repetition": repetition,
                "wall_seconds": elapsed,
                "result_fingerprint": fingerprint(repaired),
                "objective_calls": int(profile["objective_calls"]),
                "checker_calls": int(profile["check_solution_feasible_calls"]),
                "compute_timing_calls": int(profile["compute_timing_calls"]),
                "compute_timing_cache_hits": int(profile["compute_timing_cache_hits"]),
                "state_copy_calls": int(profile["state_copy_calls"]),
                "regret_exact_cache": cache,
                "peak_working_set_bytes": memory.peak_working_set,
                "peak_private_bytes": memory.peak_private,
            }
        )
        print(json.dumps({"event": "optimized_replay", **runs[-1]}), flush=True)

    payload = {
        "prefix_solver_seconds": result.runtime_seconds,
        "prefix_phase_timings": result.phase_timings,
        "prefix_history": result.history,
        "prefix_regret_call_durations": call_durations,
        "prefix_peak_working_set_bytes": prefix_memory.peak_working_set,
        "prefix_peak_private_bytes": prefix_memory.peak_private,
        "focused_runs": runs,
        "focused_median_seconds": statistics.median(
            item["wall_seconds"] for item in runs
        ),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"event": "optimized_complete", **payload}), flush=True)


if __name__ == "__main__":
    main()
