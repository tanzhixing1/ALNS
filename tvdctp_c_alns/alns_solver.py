from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from config import TVDConfig
from dataset_loader import InstanceData
from initial_solution import initial_solution
from objective import objective
from operators import DESTROY_OPERATORS, REPAIR_OPERATORS, consolidate_drone_sorties
from state import TVDState


@dataclass
class ALNSResult:
    initial_state: TVDState
    best_state: TVDState
    current_state: TVDState
    history: List[Dict[str, object]]
    runtime_seconds: float
    destroy_weights: Dict[str, float]
    repair_weights: Dict[str, float]


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

    rng = np.random.default_rng(config.alns.random_seed)
    start = time.perf_counter()

    initial = consolidate_drone_sorties(initial_solution(data, config), data, config)
    current = initial.copy()
    best = initial.copy()
    current_cost, _ = objective(current, data, config)
    best_cost, _ = objective(best, data, config)

    destroy_names = list(DESTROY_OPERATORS.keys())
    repair_names = list(REPAIR_OPERATORS.keys())
    destroy_weights = {name: 1.0 for name in destroy_names}
    repair_weights = {name: 1.0 for name in repair_names}
    destroy_scores = {name: 0.0 for name in destroy_names}
    repair_scores = {name: 0.0 for name in repair_names}
    destroy_counts = {name: 0 for name in destroy_names}
    repair_counts = {name: 0 for name in repair_names}

    history: List[Dict[str, object]] = []
    temperature = config.alns.initial_temperature
    no_improvement = 0

    for iteration in range(1, config.alns.max_iterations + 1):
        destroy_name = _roulette_choice(rng, destroy_names, destroy_weights)
        repair_name = _roulette_choice(rng, repair_names, repair_weights)

        destroyed = DESTROY_OPERATORS[destroy_name](current.copy(), rng, data, config)
        candidate = REPAIR_OPERATORS[repair_name](destroyed, rng, data, config)
        candidate_cost, candidate_breakdown = objective(candidate, data, config)
        candidate_feasible = bool(candidate_breakdown.get("feasible", False))

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
            no_improvement = 0
        elif candidate_feasible and candidate_cost < current_cost:
            outcome_score = config.alns.scores[1]
            no_improvement += 1
        elif candidate_feasible and accepted:
            outcome_score = config.alns.scores[2]
            no_improvement += 1
        else:
            no_improvement += 1

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
                "destroy": destroy_name,
                "repair": repair_name,
                "temperature": temperature,
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

        temperature *= config.alns.cooling_rate
        if no_improvement >= config.alns.max_no_improvement:
            no_improvement = 0

    runtime = time.perf_counter() - start
    objective(best, data, config)
    return ALNSResult(
        initial_state=initial,
        best_state=best,
        current_state=current,
        history=history,
        runtime_seconds=runtime,
        destroy_weights=destroy_weights,
        repair_weights=repair_weights,
    )
