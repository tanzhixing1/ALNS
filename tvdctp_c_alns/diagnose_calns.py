from __future__ import annotations

import argparse
import cProfile
import io
import json
import math
import pstats
import statistics
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import operators
from alns_profile import reset_profile, snapshot_profile
from alns_solver import run_c_alns
from config import TVDConfig, build_config
from dataset_loader import InstanceData, generate_toy_data
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from objective import objective


CURRENT_DESTROY = dict(operators.DESTROY_OPERATORS)
CURRENT_REPAIR = dict(operators.REPAIR_OPERATORS)
PAPER_DESTROY_NAMES = [
    "random_customer_removal",
    "greedy_removal",
    "related_customer_removal",
    "cascade_aware_removal",
]
PAPER_REPAIR_NAMES = [
    "best_mode_repair",
    "greedy_van_repair",
    "regret_repair",
    "cascade_repair",
]
PAPER_REPAIR_LABELS = {
    "best_mode_repair": "global greedy repair",
    "greedy_van_repair": "local greedy repair",
    "regret_repair": "regret-based repair",
    "cascade_repair": "multi-node cascade repair",
}


@contextmanager
def operator_set(name: str):
    old_destroy = dict(operators.DESTROY_OPERATORS)
    old_repair = dict(operators.REPAIR_OPERATORS)
    if name == "paper_4x4":
        operators.DESTROY_OPERATORS.clear()
        operators.DESTROY_OPERATORS.update(
            {key: CURRENT_DESTROY[key] for key in PAPER_DESTROY_NAMES}
        )
        operators.REPAIR_OPERATORS.clear()
        operators.REPAIR_OPERATORS.update(
            {key: CURRENT_REPAIR[key] for key in PAPER_REPAIR_NAMES}
        )
    elif name == "current":
        operators.DESTROY_OPERATORS.clear()
        operators.DESTROY_OPERATORS.update(CURRENT_DESTROY)
        operators.REPAIR_OPERATORS.clear()
        operators.REPAIR_OPERATORS.update(CURRENT_REPAIR)
    else:
        raise ValueError(f"unknown operator set: {name}")
    try:
        yield
    finally:
        operators.DESTROY_OPERATORS.clear()
        operators.DESTROY_OPERATORS.update(old_destroy)
        operators.REPAIR_OPERATORS.clear()
        operators.REPAIR_OPERATORS.update(old_repair)


def make_config(seed: int, iterations: int, early_stop: bool) -> TVDConfig:
    config = build_config(
        num_customers=10,
        num_orders=10,
        num_transshipments=2,
        num_containers=1,
        container_origin="port",
        iterations=iterations,
        seed=seed,
        drone_enabled=True,
        max_no_improve=100,
        early_stop_enabled=early_stop,
        output_dir="outputs/diagnostics_seed42",
    )
    config.alns.customer_removal_ratio = 0.2
    config.alns.initial_temperature = 1000.0
    config.alns.cooling_rate = 0.9995
    config.alns.weight_update_interval = 50
    config.alns.reaction_coefficient = 0.2
    return config


def count_improvements(history: List[Dict[str, object]], initial_cost: float) -> Tuple[int, int]:
    previous_best = float(initial_cost)
    improved = 0
    last = 0
    for item in history:
        best_cost = float(item.get("best_cost", previous_best))
        if best_cost < previous_best - 1e-9:
            improved += 1
            last = int(item["iteration"])
            previous_best = best_cost
    return improved, last


def active_van_routes(state) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    return {
        str(van_id): [int(node) for node in route]
        for van_id, route in sorted(routes.items())
        if len(route) > 2
    }


def local_ratio(profile: Dict[str, object]) -> Tuple[int, int, float | None]:
    repair_stats = profile.get("repair", {})
    candidates = sum(int(stats.get("candidate_count", 0)) for stats in repair_stats.values())
    feasible = sum(
        int(stats.get("feasible_candidate_count", 0))
        for stats in repair_stats.values()
    )
    return candidates, feasible, feasible / candidates if candidates else None


def summarize_result(operator_set_name: str, seed: int, config: TVDConfig, data: InstanceData, result) -> Dict[str, object]:
    initial_cost, initial_breakdown = objective(result.initial_state, data, config)
    best_cost, best_breakdown = objective(result.best_state, data, config)
    feasible, violations = check_solution_feasible(result.best_state, data, config)
    if not feasible or violations:
        raise RuntimeError(f"infeasible best: {violations}")
    improved, last_improvement = count_improvements(result.history, initial_cost)
    full_feasible = sum(1 for item in result.history if item.get("candidate_feasible"))
    accepted = sum(1 for item in result.history if item.get("accepted"))
    local_candidates, local_feasible, local_feasible_ratio = local_ratio(result.profile)
    timing = result.best_state.timing or {}
    return {
        "operator_set_name": operator_set_name,
        "seed": seed,
        "runtime_seconds": round(float(result.runtime_seconds), 6),
        "actual_iterations": int(result.actual_iterations),
        "initial_cost": float(initial_cost),
        "best_cost": float(best_cost),
        "improvement_abs": float(initial_cost - best_cost),
        "improvement_pct": float((initial_cost - best_cost) / initial_cost * 100.0),
        "best_feasible": bool(feasible),
        "violations_count": int(len(violations)),
        "accepted_candidates": int(accepted),
        "improved_candidates": int(improved),
        "last_improvement_iteration": int(last_improvement),
        "full_candidate_feasible_ratio": full_feasible / len(result.history)
        if result.history
        else None,
        "local_repair_feasible_ratio": local_feasible_ratio,
        "local_repair_candidates": local_candidates,
        "local_repair_feasible_candidates": local_feasible,
        "best_van_routes": active_van_routes(result.best_state),
        "best_drone_sorties_count": int(len(result.best_state.drone_sorties)),
        "unassigned_customers": [int(customer) for customer in result.best_state.unassigned],
        "time_window_violations": int(
            best_breakdown.get(
                "num_time_window_violations",
                len(timing.get("time_window_violations", [])),
            )
        ),
        "no_improve_counter_at_end": int(result.no_improve_counter),
        "early_stop_triggered": bool(result.early_stop_triggered),
        "initial_breakdown": initial_breakdown,
        "best_breakdown": best_breakdown,
        "phase_timings": result.phase_timings,
        "initial_timing": result.initial_state.metadata.get("initial_timing", {}),
        "initial_state_copy_count": int(
            result.initial_state.metadata.get("initial_state_copy_count", 0)
        ),
        "initial_deepcopy_count": int(
            result.initial_state.metadata.get("initial_deepcopy_count", 0)
        ),
        "profile": result.profile,
        "history": result.history,
    }


def run_case(
    operator_set_name: str,
    seed: int,
    iterations: int,
    early_stop: bool,
    *,
    data_seed: int = 42,
) -> Dict[str, object]:
    config = make_config(data_seed, iterations, early_stop)
    t0 = time.perf_counter()
    data = generate_toy_data(config)
    t_data = time.perf_counter() - t0
    config.alns.random_seed = int(seed)
    with operator_set(operator_set_name):
        result = run_c_alns(data, config)
    row = summarize_result(operator_set_name, seed, config, data, result)
    row["max_iterations"] = iterations
    row["early_stop_enabled"] = early_stop
    row["max_no_improve"] = 100
    row["t_data_generation"] = t_data
    row["t_total"] = t_data + float(result.runtime_seconds)
    return row


def run_initial_only(seed: int) -> Dict[str, object]:
    config = make_config(seed, 0, False)
    t0 = time.perf_counter()
    data = generate_toy_data(config)
    t_data = time.perf_counter() - t0
    reset_profile()
    t1 = time.perf_counter()
    state = initial_solution(data, config)
    t_initial = time.perf_counter() - t1
    t2 = time.perf_counter()
    initial_cost, _ = objective(state, data, config)
    t_obj = time.perf_counter() - t2
    t3 = time.perf_counter()
    feasible, violations = check_solution_feasible(state, data, config)
    t_check = time.perf_counter() - t3
    profile = snapshot_profile()
    return {
        "run_type": "initial_only",
        "seed": seed,
        "max_iterations": 0,
        "early_stop_enabled": False,
        "actual_iterations": 0,
        "t_data_generation": t_data,
        "t_initial_solution_total": t_initial,
        "t_initial_objective": t_obj,
        "t_initial_feasibility_check": t_check,
        "t_alns_loop": 0.0,
        "t_final_feasibility_check": 0.0,
        "t_profile_output": 0.0,
        "t_total": t_data + t_initial + t_obj + t_check,
        "ms_per_iteration": None,
        "initial_cost": initial_cost,
        "best_cost": initial_cost,
        "best_feasible": feasible,
        "violations_count": len(violations),
        "last_improvement_iteration": 0,
        "improved_candidates": 0,
        "accepted_candidates": 0,
        "initial_timing": state.metadata.get("initial_timing", {}),
        "initial_state_copy_count": state.metadata.get("initial_state_copy_count", 0),
        "initial_deepcopy_count": state.metadata.get("initial_deepcopy_count", 0),
        "profile": profile,
    }


def phase_row(run_type: str, row: Dict[str, object]) -> Dict[str, object]:
    phases = row.get("phase_timings", {})
    actual = int(row.get("actual_iterations", 0))
    return {
        "run_type": run_type,
        "seed": row["seed"],
        "max_iterations": row.get("max_iterations", 0),
        "early_stop_enabled": row.get("early_stop_enabled", False),
        "actual_iterations": actual,
        "t_data_generation": row.get("t_data_generation", 0.0),
        "t_initial_solution_total": phases.get(
            "t_initial_solution_total", row.get("t_initial_solution_total", 0.0)
        ),
        "t_initial_objective": phases.get(
            "t_initial_objective", row.get("t_initial_objective", 0.0)
        ),
        "t_initial_feasibility_check": phases.get(
            "t_initial_feasibility_check",
            row.get("t_initial_feasibility_check", 0.0),
        ),
        "t_alns_loop": phases.get("t_alns_loop", row.get("t_alns_loop", 0.0)),
        "t_final_feasibility_check": phases.get(
            "t_final_feasibility_check", row.get("t_final_feasibility_check", 0.0)
        ),
        "t_profile_output": phases.get(
            "t_profile_output", row.get("t_profile_output", 0.0)
        ),
        "t_total": row.get("t_total", 0.0),
        "ms_per_iteration": (
            phases.get("t_alns_loop", 0.0) / actual * 1000.0 if actual else None
        ),
        "initial_cost": row["initial_cost"],
        "best_cost": row["best_cost"],
        "best_feasible": row["best_feasible"],
        "violations_count": row["violations_count"],
        "last_improvement_iteration": row["last_improvement_iteration"],
        "improved_candidates": row["improved_candidates"],
        "accepted_candidates": row["accepted_candidates"],
    }


def profile_on(seed: int = 42) -> Dict[str, object]:
    profiler = cProfile.Profile()
    profiler.enable()
    row = run_case("current", seed, 1000, True)
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative")
    stats.print_stats(10)
    profile = row["profile"]
    function_times = {}
    for func, stat in stats.stats.items():
        filename, lineno, name = func
        key = f"{Path(filename).name}:{lineno}({name})"
        function_times[key] = {
            "calls": stat[0],
            "primitive_calls": stat[1],
            "total_time": stat[2],
            "cumulative_time": stat[3],
        }

    def cum_contains(token: str) -> float:
        return sum(
            item["cumulative_time"]
            for key, item in function_times.items()
            if token in key
        )

    hits = (
        int(profile.get("check_solution_feasible_cache_hits", 0))
        + int(profile.get("compute_timing_cache_hits", 0))
        + int(profile.get("objective_cache_hits", 0))
    )
    misses = int(profile.get("cache_misses", 0))
    return {
        "row": row,
        "check_solution_feasible_calls": profile.get("check_solution_feasible_calls", 0),
        "compute_timing_calls": profile.get("compute_timing_calls", 0),
        "objective_calls": profile.get("objective_calls", 0),
        "TVDState.copy_calls": profile.get("state_copy_calls", 0),
        "copy.deepcopy_calls": profile.get("state_deepcopy_calls", 0),
        "copy_time_total": cum_contains("state.py") if False else cum_contains("(copy)"),
        "deepcopy_time_total": cum_contains("copy.py"),
        "compute_timing_time_total": cum_contains("compute_timing"),
        "check_solution_feasible_time_total": cum_contains("check_solution_feasible"),
        "objective_time_total": cum_contains("objective"),
        "state_signature_time_total": profile.get("state_signature_time_total", 0.0),
        "cache_hit_count": hits,
        "cache_miss_count": misses,
        "cache_hit_ratio": hits / (hits + misses) if hits + misses else None,
        "top_10_functions_by_cumulative_time": stream.getvalue(),
    }


def objective_breakdown(row: Dict[str, object]) -> List[Dict[str, object]]:
    result = []
    for label, breakdown in [
        ("initial", row["initial_breakdown"]),
        ("best", row["best_breakdown"]),
    ]:
        result.append(
            {
                "solution": label,
                "tractor_travel_cost": breakdown.get("truck_transport_cost", 0.0),
                "van_travel_cost": breakdown.get("van_transport_cost", 0.0),
                "drone_travel_cost": breakdown.get("drone_transport_cost", 0.0),
                "tractor_fixed_cost": breakdown.get("truck_fixed_cost", 0.0),
                "van_fixed_cost": breakdown.get("van_fixed_cost", 0.0),
                "drone_fixed_cost": breakdown.get("drone_fixed_cost", 0.0),
                "waiting_cost": breakdown.get("waiting_cost", 0.0),
                "penalty_cost": breakdown.get("penalty_cost", 0.0),
                "total_cost_current_code": breakdown.get("total_cost", 0.0),
                "waiting_cost_reported_not_optimized": breakdown.get(
                    "waiting_cost_reported_not_optimized", None
                ),
            }
        )
    return result


def operator_catalog() -> List[Dict[str, object]]:
    rows = []
    paper_destroy = set(PAPER_DESTROY_NAMES)
    paper_repair = set(PAPER_REPAIR_NAMES)
    for name in CURRENT_DESTROY:
        rows.append(
            {
                "operator_name": name,
                "paper_label": name,
                "operator_type": "destroy",
                "is_paper_operator": name in paper_destroy,
                "is_extra_operator": name not in paper_destroy,
            }
        )
    for name in CURRENT_REPAIR:
        rows.append(
            {
                "operator_name": name,
                "paper_label": PAPER_REPAIR_LABELS.get(name, name),
                "operator_type": "repair",
                "is_paper_operator": name in paper_repair,
                "is_extra_operator": name not in paper_repair,
            }
        )
    return rows


def operator_contribution(row: Dict[str, object]) -> List[Dict[str, object]]:
    pairs = row["profile"].get("operator_pairs", {})
    result = []
    for stats in pairs.values():
        calls = int(stats.get("calls", 0))
        result.append(
            {
                "destroy_operator": stats.get("destroy_operator"),
                "repair_operator": stats.get("repair_operator"),
                "calls": calls,
                "generated_candidates": stats.get("generated_candidates", 0),
                "local_feasible_candidates": stats.get("local_feasible_candidates", 0),
                "full_feasible_candidates": stats.get("full_feasible_candidates", 0),
                "accepted_candidates": stats.get("accepted_candidates", 0),
                "improved_candidates": stats.get("improved_candidates", 0),
                "total_runtime": stats.get("total_runtime", 0.0),
                "avg_runtime_per_call": (
                    stats.get("total_runtime", 0.0) / calls if calls else None
                ),
                "best_improvement_contributed": stats.get(
                    "best_improvement_contributed", 0.0
                ),
                "average_delta_cost": (
                    stats.get("delta_cost_sum", 0.0) / calls if calls else None
                ),
                "selected_weight_start": stats.get("selected_weight_start"),
                "selected_weight_end": stats.get("selected_weight_end"),
            }
        )
    return sorted(result, key=lambda item: (-item["calls"], str(item["destroy_operator"])))


def repair_failure(row: Dict[str, object]) -> Dict[str, object]:
    profile = row["profile"]
    destroy = profile.get("destroy", {})
    counts = destroy.get("removed_customer_counts", [])
    cascade = destroy.get("cascade_expansion_counts", [])
    rejections = profile.get("repair_rejections", {})
    full_viols = {
        key.replace("full_violation:", ""): value
        for key, value in rejections.items()
        if str(key).startswith("full_violation:")
    }
    top_violations = sorted(full_viols.items(), key=lambda item: item[1], reverse=True)[:10]
    return {
        "avg_removed_customer_count": statistics.mean(counts) if counts else 0.0,
        "min_removed_customer_count": min(counts) if counts else 0,
        "max_removed_customer_count": max(counts) if counts else 0,
        "removed_high_floor_count": destroy.get("removed_high_floor_count", 0),
        "removed_drone_customer_count": destroy.get("removed_drone_customer_count", 0),
        "removed_van_customer_count": destroy.get("removed_van_customer_count", 0),
        "cascade_expansion_count_avg": statistics.mean(cascade) if cascade else 0.0,
        "van_insert_candidates": profile.get("van_insert_candidates", 0),
        "drone_insert_candidates": profile.get("drone_insert_candidates", 0),
        "service_mode_switch_candidates": profile.get("service_mode_switch_candidates", 0),
        "cross_van_docking_candidates": profile.get("cross_van_docking_candidates", 0),
        "new_van_activation_candidates": profile.get("new_van_activation_candidates", 0),
        "rejected_by_capacity": rejections.get("rejected_by_capacity", 0),
        "rejected_by_time_window": rejections.get("rejected_by_time_window", 0),
        "rejected_by_drone_payload": rejections.get("rejected_by_drone_payload", 0),
        "rejected_by_drone_endurance": rejections.get("rejected_by_drone_endurance", 0),
        "rejected_by_drone_energy": rejections.get("rejected_by_drone_energy", 0),
        "rejected_by_sync": rejections.get("rejected_by_sync", 0),
        "rejected_by_full_feasibility": rejections.get("rejected_by_full_feasibility", 0),
        "full_feasibility_failed_top_10_violation_types": top_violations,
    }


def sa_diagnostics(row: Dict[str, object]) -> Dict[str, object]:
    history = row["history"]
    better = [item for item in history if float(item.get("delta_cost_from_current", 0.0)) < -1e-9]
    worse = [item for item in history if float(item.get("delta_cost_from_current", 0.0)) > 1e-9]
    equal = [
        item
        for item in history
        if abs(float(item.get("delta_cost_from_current", 0.0))) <= 1e-9
    ]
    checkpoints = {}
    for idx in [0, 50, 100, 150, 200, 500, 1000]:
        checkpoints[f"temperature_iter_{idx}"] = 1000.0 * (0.9995 ** idx)
    accepted = [item for item in history if item.get("accepted")]
    improved = [item for item in history if item.get("is_global_best_improvement")]
    return {
        "initial_temperature": 1000.0,
        "cooling_rate": 0.9995,
        **checkpoints,
        "final_temperature": 1000.0 * (0.9995 ** len(history)),
        "better_candidate_count": len(better),
        "better_accepted_count": sum(1 for item in better if item.get("accepted")),
        "worse_candidate_count": len(worse),
        "worse_accepted_count": sum(1 for item in worse if item.get("accepted")),
        "worse_acceptance_rate": (
            sum(1 for item in worse if item.get("accepted")) / len(worse)
            if worse
            else None
        ),
        "equal_candidate_count": len(equal),
        "rejected_count": len(history) - len(accepted),
        "accepted_count": len(accepted),
        "accepted_but_not_improved_count": len(accepted) - len(improved),
        "improved_count": len(improved),
    }


def instance_summary(seed: int = 42) -> Dict[str, object]:
    config = make_config(seed, 1000, False)
    data = generate_toy_data(config)
    widths = {
        customer: data.time_windows[customer][1] - data.time_windows[customer][0]
        for customer in data.customers
    }
    tight = [customer for customer, width in widths.items() if width <= 120.0]
    imports = 0
    exports = 0
    both = 0
    for customer in data.customers:
        d = float(data.demands.get(customer, 0.0))
        p = float(data.pickup_demands.get(customer, 0.0))
        if d > 0 and p > 0:
            both += 1
        elif d > 0:
            imports += 1
        elif p > 0:
            exports += 1
    xs = [coord[0] for coord in data.coordinates.values()]
    ys = [coord[1] for coord in data.coordinates.values()]
    demands = list(data.demands.values())
    ineligible = [
        customer for customer, eligible in data.drone_eligible.items() if not eligible
    ]
    return {
        "num_customers": len(data.customers),
        "num_containers": config.data.num_containers,
        "num_warehouses": len(data.transshipment_nodes),
        "vans_per_warehouse": config.warehouse_num_vans(data.transshipment_nodes),
        "drones_per_van": config.fleet.drones_per_van,
        "high_floor_customers": [
            customer for customer, high in data.is_high_floor.items() if high
        ],
        "high_floor_ratio": sum(data.is_high_floor.values()) / len(data.customers),
        "tight_time_window_customers": tight,
        "tight_time_window_ratio": len(tight) / len(data.customers),
        "request_type_ratio import/export/both": {
            "import": imports / len(data.customers),
            "export": exports / len(data.customers),
            "both": both / len(data.customers),
        },
        "demand_min/max/avg": [min(demands), max(demands), statistics.mean(demands)],
        "drone_ineligible_count": len(ineligible),
        "drone_ineligible_reasons": [] if not ineligible else ["data.drone_eligible=False"],
        "service_region_size": {
            "x_range": max(xs) - min(xs),
            "y_range": max(ys) - min(ys),
        },
        "distance_metric": f"Euclidean; road factor={config.data.road_distance_factor}",
        "vehicle_speeds": {
            "tractor": config.fleet.tractor_speed_kmph,
            "van": config.fleet.van_speed_kmph,
            "drone": config.fleet.drone_speed_kmph,
        },
        "cost_parameters": {
            "tractor_cost_per_km": config.cost.tractor_cost_per_km,
            "van_cost_per_km": config.cost.van_cost_per_km,
            "drone_cost_per_km": config.cost.drone_cost_per_km,
        },
        "fixed_costs": {
            "tractor": config.cost.tractor_fixed_cost,
            "trailer": config.cost.trailer_fixed_cost,
            "van": config.cost.van_fixed_cost,
            "drone": config.cost.drone_fixed_cost,
        },
        "time_penalty_cost": config.cost.time_penalty_per_hour,
    }


def summarize_seeds(rows: List[Dict[str, object]]) -> Dict[str, object]:
    costs = [float(row["best_cost"]) for row in rows]
    runtimes = [float(row["runtime_seconds"]) for row in rows]
    improved = [int(row["improved_candidates"]) for row in rows]
    best = min(rows, key=lambda row: float(row["best_cost"]))
    worst = max(rows, key=lambda row: float(row["best_cost"]))
    mean = statistics.mean(costs)
    std = statistics.pstdev(costs) if len(costs) > 1 else 0.0
    return {
        "mean_best_cost": mean,
        "min_best_cost": min(costs),
        "max_best_cost": max(costs),
        "std_best_cost": std,
        "coefficient_of_variation": std / mean if mean else None,
        "mean_runtime": statistics.mean(runtimes),
        "min_runtime": min(runtimes),
        "max_runtime": max(runtimes),
        "mean_improved_candidates": statistics.mean(improved),
        "best_seed": int(best["seed"]),
        "worst_seed": int(worst["seed"]),
        "any_seed_below_789_343": any(cost < 789.343 - 1e-9 for cost in costs),
    }


def run_core(outdir: Path) -> Dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    initial = run_initial_only(42)
    rows = {
        "initial_only": initial,
        "zero_iterations": run_case("current", 42, 0, False),
        "iter80": run_case("current", 42, 80, False),
        "iter1000_early": run_case("current", 42, 1000, True),
    }
    fixed_current = run_case("current", 42, 1000, False)
    fixed_paper = run_case("paper_4x4", 42, 1000, False)
    early_current = rows["iter1000_early"]
    early_paper = run_case("paper_4x4", 42, 1000, True)
    prof = profile_on(42)
    result = {
        "phase_rows": [
            phase_row("initial_only", initial),
            phase_row("0_iterations", rows["zero_iterations"]),
            phase_row("80_iterations", rows["iter80"]),
            phase_row("1000_early_stop", rows["iter1000_early"]),
        ],
        "profile_off": phase_row("1000_early_stop", rows["iter1000_early"]),
        "profile_on": prof,
        "objective_breakdown": objective_breakdown(rows["iter1000_early"]),
        "operator_catalog": operator_catalog(),
        "fixed_iteration_comparison": [fixed_current, fixed_paper],
        "early_stop_comparison": [early_current, early_paper],
        "operator_contribution": operator_contribution(fixed_current),
        "repair_failure": repair_failure(fixed_current),
        "sa_diagnostics": sa_diagnostics(fixed_current),
        "initial_solution_timing": rows["iter1000_early"]["initial_timing"],
        "initial_state_copy_count": rows["iter1000_early"]["initial_state_copy_count"],
        "initial_deepcopy_count": rows["iter1000_early"]["initial_deepcopy_count"],
        "instance_summary": instance_summary(42),
    }
    (outdir / "core_diagnostics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def run_multiseed(outdir: Path) -> Dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for operator_name in ["current", "paper_4x4"]:
        for seed in range(10):
            row = run_case(operator_name, seed, 1000, False)
            compact = compact_row(row)
            rows.append(compact)
            print(json.dumps({
                "operator_set_name": compact["operator_set_name"],
                "seed": compact["seed"],
                "runtime_seconds": compact["runtime_seconds"],
                "best_cost": compact["best_cost"],
            }), flush=True)
    grouped = {
        name: [row for row in rows if row["operator_set_name"] == name]
        for name in ["current", "paper_4x4"]
    }
    result = {
        "rows": rows,
        "summary": {name: summarize_seeds(items) for name, items in grouped.items()},
    }
    (outdir / "multiseed_diagnostics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def run_long(outdir: Path, seeds: Iterable[int]) -> Dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in seeds:
        for iterations in [2000, 5000]:
            row = run_case("current", int(seed), iterations, False)
            compact = compact_row(row)
            rows.append(compact)
            print(json.dumps({
                "seed": compact["seed"],
                "max_iterations": iterations,
                "runtime_seconds": compact["runtime_seconds"],
                "best_cost": compact["best_cost"],
            }), flush=True)
    result = {"rows": rows}
    (outdir / "long_horizon_diagnostics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def compact_row(row: Dict[str, object]) -> Dict[str, object]:
    keys = [
        "operator_set_name",
        "seed",
        "max_iterations",
        "early_stop_enabled",
        "runtime_seconds",
        "actual_iterations",
        "initial_cost",
        "best_cost",
        "improvement_abs",
        "improvement_pct",
        "best_feasible",
        "violations_count",
        "accepted_candidates",
        "improved_candidates",
        "last_improvement_iteration",
        "full_candidate_feasible_ratio",
        "local_repair_feasible_ratio",
        "best_van_routes",
        "best_drone_sorties_count",
        "unassigned_customers",
        "time_window_violations",
        "no_improve_counter_at_end",
        "early_stop_triggered",
    ]
    return {key: row.get(key) for key in keys}


def check_gurobi() -> Dict[str, object]:
    try:
        import gurobipy  # type: ignore  # noqa: F401
    except Exception as exc:
        return {
            "method": "Gurobi/MILP",
            "time_limit": 300,
            "runtime_seconds": 0.0,
            "incumbent_cost": None,
            "lower_bound": None,
            "gap": None,
            "status": f"unavailable: {exc}",
            "feasible": None,
        }
    return {
        "method": "Gurobi/MILP",
        "time_limit": 300,
        "runtime_seconds": 0.0,
        "incumbent_cost": None,
        "lower_bound": None,
        "gap": None,
        "status": "gurobipy importable, but no project MILP runner was found",
        "feasible": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["core", "multiseed", "long", "gurobi"], required=True)
    parser.add_argument("--outdir", default="tvdctp_c_alns/outputs/diagnostics_seed42")
    parser.add_argument("--seeds", default="")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    if args.mode == "core":
        result = run_core(outdir)
    elif args.mode == "multiseed":
        result = run_multiseed(outdir)
    elif args.mode == "long":
        seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
        result = run_long(outdir, seeds)
    else:
        result = check_gurobi()
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "gurobi_check.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
