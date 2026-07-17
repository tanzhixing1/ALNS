from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import check_solution_feasible
from initial_solution import initial_solution
from alns_profile import (
    enter_operator_pair,
    exit_operator_pair,
    record_full_candidate_diagnostic,
    record_repair_rejection,
    reset_profile,
    set_local_feasibility_cache_enabled,
    snapshot_profile,
)
from objective import objective
from operators import DESTROY_OPERATORS, REPAIR_OPERATORS, consolidate_drone_sorties
from operator_modes import (
    ActionRegistry,
    OperatorMode,
    build_action_registry,
    resolve_operator_mode,
)
from removal_structural_context import assert_no_active_removal_context
from state import TVDState
from drone_repair_diagnostics import build_full_candidate_diagnostic


@dataclass
class ALNSResult:
    initial_state: TVDState
    best_state: TVDState
    current_state: TVDState
    history: List[Dict[str, object]]
    runtime_seconds: float
    actual_iterations: int
    no_improve_counter: int
    early_stop_triggered: bool
    phase_timings: Dict[str, float]
    destroy_weights: Dict[str, float]
    repair_weights: Dict[str, float]
    profile: Dict[str, object]
    operator_mode: OperatorMode
    action_registry_fingerprint: str


def _roulette_choice(
    rng: np.random.Generator, names: List[str], weights: Dict[str, float]
) -> str:
    values = np.array([max(weights[name], 1e-9) for name in names], dtype=float)
    probs = values / values.sum()
    return str(rng.choice(names, p=probs))


def _accept(
    rng: np.random.Generator,
    current_cost: float,
    candidate_cost: float,
    temperature: float,
) -> bool:
    if candidate_cost < current_cost:
        return True
    probability = math.exp(-(candidate_cost - current_cost) / max(temperature, 1e-9))
    return bool(rng.random() < probability)


def _update_weights(
    weights: Dict[str, float],
    scores: Dict[str, float],
    counts: Dict[str, int],
    reaction: float,
) -> None:
    for name in weights:
        if counts[name] == 0:
            continue
        segment_score = scores[name] / counts[name]
        weights[name] = (1.0 - reaction) * weights[name] + reaction * segment_score
        scores[name] = 0.0
        counts[name] = 0


def run_c_alns(data: InstanceData, config: TVDConfig) -> ALNSResult:
    """不含 PPO 的 C-ALNS 主循环，贴合论文第 5.1.4 节的 SA + adaptive weights。"""

    reset_profile()
    phase_timings: Dict[str, float] = {}
    phase_start = time.perf_counter()
    resolved_mode = resolve_operator_mode(
        getattr(config.alns, "operator_mode", OperatorMode.PAPER)
    )
    phase_timings["t_operator_mode_resolution"] = time.perf_counter() - phase_start
    phase_start = time.perf_counter()
    action_registry: ActionRegistry = build_action_registry(
        resolved_mode,
        DESTROY_OPERATORS,
        REPAIR_OPERATORS,
    )
    phase_timings["t_action_registry_construction"] = (
        time.perf_counter() - phase_start
    )
    set_local_feasibility_cache_enabled(
        bool(getattr(config.alns, "enable_local_feasibility_cache", False))
    )
    rng = np.random.default_rng(config.alns.random_seed)
    start = time.perf_counter()

    phase_start = time.perf_counter()
    initial = consolidate_drone_sorties(initial_solution(data, config), data, config)
    phase_timings["t_initial_solution_total"] = time.perf_counter() - phase_start
    current = initial.copy()
    best = initial.copy()
    assert_no_active_removal_context(current, owner="current")
    assert_no_active_removal_context(best, owner="best")
    phase_start = time.perf_counter()
    current_cost, _ = objective(current, data, config)
    best_cost, _ = objective(best, data, config)
    phase_timings["t_initial_objective"] = time.perf_counter() - phase_start
    phase_start = time.perf_counter()
    initial_feasible, initial_violations = check_solution_feasible(initial, data, config)
    phase_timings["t_initial_feasibility_check"] = time.perf_counter() - phase_start
    if not initial_feasible:
        raise RuntimeError(
            "C-ALNS initial solution is infeasible after final feasibility check: "
            f"{initial_violations}"
        )

    destroy_names = list(action_registry.destroy_names)
    repair_names = list(action_registry.repair_names)
    destroy_weights = {name: 1.0 for name in destroy_names}
    repair_weights = {name: 1.0 for name in repair_names}
    destroy_scores = {name: 0.0 for name in destroy_names}
    repair_scores = {name: 0.0 for name in repair_names}
    destroy_counts = {name: 0 for name in destroy_names}
    repair_counts = {name: 0 for name in repair_names}

    history: List[Dict[str, object]] = []
    phase_timings["t_operator_selection"] = 0.0
    temperature = config.alns.initial_temperature
    no_improve_counter = 0
    actual_iterations = 0
    early_stop_triggered = False
    max_no_improve = getattr(
        config.alns,
        "max_no_improve",
        getattr(config.alns, "max_no_improvement", None),
    )
    early_stop_enabled = bool(
        getattr(config.alns, "early_stop_enabled", True)
        and max_no_improve is not None
        and int(max_no_improve) > 0
    )

    loop_start = time.perf_counter()
    setattr(config.alns, "_inside_alns_loop", True)
    for iteration in range(1, config.alns.max_iterations + 1):
        actual_iterations = iteration
        selection_start = time.perf_counter()
        destroy_name = _roulette_choice(rng, destroy_names, destroy_weights)
        repair_name = _roulette_choice(rng, repair_names, repair_weights)
        action = action_registry.action_for_id(
            action_registry.action_id_for_pair(destroy_name, repair_name)
        )
        phase_timings["t_operator_selection"] += (
            time.perf_counter() - selection_start
        )
        destroy_weight_start = float(destroy_weights[destroy_name])
        repair_weight_start = float(repair_weights[repair_name])
        previous_best_cost = float(best_cost)
        previous_current_cost = float(current_cost)

        assert_no_active_removal_context(current, owner="current")
        assert_no_active_removal_context(best, owner="best")
        enter_operator_pair(destroy_name, repair_name)
        destroyed = action_registry.destroy_operator(destroy_name)(
            current.copy(), rng, data, config
        )
        candidate = action_registry.repair_operator(repair_name)(
            destroyed, rng, data, config
        )
        assert_no_active_removal_context(candidate, owner="repair-returned candidate")
        candidate_cost, candidate_breakdown = objective(candidate, data, config)
        candidate_feasible = bool(candidate_breakdown.get("feasible", False))
        shadow_failures = []
        if bool(getattr(config.alns, "diagnostics_shadow", False)):
            from drone_repair_diagnostics import (
                shadow_state_failures,
                summarize_failure_reasons,
            )

            shadow_failures = shadow_state_failures(candidate, data, config)
            shadow_summary = summarize_failure_reasons(shadow_failures)
        else:
            shadow_summary = {}
        if not candidate_feasible:
            if bool(getattr(config.alns, "collect_full_candidate_diagnostics", False)):
                record_full_candidate_diagnostic(
                    build_full_candidate_diagnostic(
                        iteration=iteration,
                        destroy_operator=destroy_name,
                        repair_operator=repair_name,
                        candidate=candidate,
                        candidate_objective=candidate_cost,
                        violations=candidate_breakdown.get("violations", []),
                        data=data,
                    )
                )
            record_repair_rejection("rejected_by_full_feasibility")
            for violation in candidate_breakdown.get("violations", [])[:20]:
                violation_type = str(violation).split(":", 1)[0].split(".")[0]
                record_repair_rejection(f"full_violation:{violation_type}")

        accepted = (
            _accept(rng, current_cost, candidate_cost, temperature)
            if candidate_feasible
            else False
        )
        outcome_score = config.alns.scores[3]

        if candidate_feasible and candidate_cost < best_cost:
            best = candidate.copy()
            best_cost = candidate_cost
            outcome_score = config.alns.scores[0]
            no_improve_counter = 0
        elif candidate_feasible and candidate_cost < current_cost:
            outcome_score = config.alns.scores[1]
            no_improve_counter += 1
        elif candidate_feasible and accepted:
            outcome_score = config.alns.scores[2]
            no_improve_counter += 1
        else:
            no_improve_counter += 1

        if accepted:
            current = candidate
            current_cost = candidate_cost

        destroy_scores[destroy_name] += outcome_score
        repair_scores[repair_name] += outcome_score
        destroy_counts[destroy_name] += 1
        repair_counts[repair_name] += 1

        history.append(
            {
                "iteration": iteration,
                "current_cost": current_cost,
                "candidate_cost": candidate_cost,
                "best_cost": best_cost,
                "accepted": accepted,
                "candidate_feasible": candidate_feasible,
                "shadow_failed": bool(shadow_failures),
                "shadow_fail_reasons": shadow_summary,
                "shadow_fail_samples": shadow_failures[:20],
                "destroy": destroy_name,
                "repair": repair_name,
                "action_id": action.action_id,
                "action_display_name": action.display_name,
                "operator_mode": resolved_mode.value,
                "action_registry_fingerprint": action_registry.fingerprint,
                "temperature": temperature,
                "no_improve_counter": no_improve_counter,
                "is_global_best_improvement": (
                    candidate_feasible and candidate_cost < previous_best_cost
                ),
                "delta_cost_from_current": candidate_cost - previous_current_cost,
                **candidate_breakdown,
            }
        )

        if iteration % config.alns.weight_update_interval == 0:
            _update_weights(
                destroy_weights,
                destroy_scores,
                destroy_counts,
                config.alns.reaction_coefficient,
            )
            _update_weights(
                repair_weights,
                repair_scores,
                repair_counts,
                config.alns.reaction_coefficient,
            )

        exit_operator_pair(
            destroy_name,
            repair_name,
            candidate_feasible=candidate_feasible,
            accepted=accepted,
            improved=candidate_feasible and candidate_cost < previous_best_cost,
            delta_cost=candidate_cost - previous_current_cost,
            best_improvement=max(0.0, previous_best_cost - candidate_cost),
            selected_weight_start=destroy_weight_start * repair_weight_start,
            selected_weight_end=float(destroy_weights[destroy_name])
            * float(repair_weights[repair_name]),
        )

        temperature *= config.alns.cooling_rate
        if early_stop_enabled and no_improve_counter >= int(max_no_improve):
            early_stop_triggered = True
            break

    setattr(config.alns, "_inside_alns_loop", False)
    assert_no_active_removal_context(current, owner="current")
    assert_no_active_removal_context(best, owner="best")
    phase_timings["t_alns_loop"] = time.perf_counter() - loop_start
    runtime = time.perf_counter() - start
    phase_start = time.perf_counter()
    objective(best, data, config)
    phase_timings["t_final_objective"] = time.perf_counter() - phase_start
    phase_start = time.perf_counter()
    best_feasible, best_violations = check_solution_feasible(best, data, config)
    phase_timings["t_final_feasibility_check"] = time.perf_counter() - phase_start
    best.metadata["feasible"] = best_feasible
    best.metadata["feasibility_violations"] = best_violations
    if not best_feasible:
        raise RuntimeError(
            "C-ALNS best solution is infeasible after final feasibility check: "
            f"{best_violations}"
        )
    phase_start = time.perf_counter()
    profile = snapshot_profile()
    phase_timings["t_profile_output"] = time.perf_counter() - phase_start
    return ALNSResult(
        initial_state=initial,
        best_state=best,
        current_state=current,
        history=history,
        runtime_seconds=runtime,
        actual_iterations=actual_iterations,
        no_improve_counter=no_improve_counter,
        early_stop_triggered=early_stop_triggered,
        phase_timings=phase_timings,
        destroy_weights=destroy_weights,
        repair_weights=repair_weights,
        profile=profile,
        operator_mode=resolved_mode,
        action_registry_fingerprint=action_registry.fingerprint,
    )
