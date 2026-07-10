from __future__ import annotations

from collections import Counter
import re
from typing import Dict, Iterable, List, Tuple

from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import compute_timing, sortie_nodes
from state import TVDState


_VIOLATION_CATEGORY_RULES = (
    ("A_position_node_reference", ("position", "node", "van_route")),
    ("B_timing_synchronization", ("time", "timing", "synchron", "window", "ready", "arrival", "departure")),
    ("C_physical_carrier_resource", ("physical drone", "carried", "carrier", "dynamic", "capacity")),
    ("D_sortie_structure", ("sortie", "relaunch", "overlap", "ordering", "terminal warehouse")),
    ("E_payload_energy", ("payload", "endurance", "battery", "energy")),
    ("F_service_completeness", ("duplicate", "unassigned", "missing", "high-floor", "served more than once")),
    ("G_van_container_structure", ("van", "container", "tractor", "trailer", "warehouse")),
)


def classify_violation(violation: str) -> str:
    """Map a full-checker message to a stable diagnostic category."""

    text = str(violation).lower()
    for category, tokens in _VIOLATION_CATEGORY_RULES:
        if any(token in text for token in tokens):
            return category
    return "H_unknown_uncategorized"


def _int_values(text: str) -> List[int]:
    return [int(value) for value in re.findall(r"(?<![A-Za-z_])-?\d+", text)]


def _affected_customers(violations: Iterable[str], data: InstanceData) -> List[int]:
    customer_ids = {int(customer) for customer in data.customers}
    result = set()
    for violation in violations:
        result.update(value for value in _int_values(str(violation)) if value in customer_ids)
    return sorted(result)


def _affected_ids(violations: Iterable[str], prefix: str) -> List[str]:
    result = set()
    for violation in violations:
        result.update(re.findall(rf"{re.escape(prefix)}[A-Za-z0-9_-]+", str(violation)))
    return sorted(result)


def _candidate_source(repair_operator: str) -> str:
    source_by_operator = {
        "greedy_van_repair": "van insertion",
        "greedy_drone_repair": "drone insertion",
        "best_mode_repair": "best-mode repair",
        "regret_repair": "regret combination",
        "cascade_repair": "cascade bundle",
    }
    return source_by_operator.get(str(repair_operator), "finish repair")


def build_full_candidate_diagnostic(
    *,
    iteration: int,
    destroy_operator: str,
    repair_operator: str,
    candidate: TVDState,
    candidate_objective: float,
    violations: Iterable[str],
    data: InstanceData,
) -> Dict[str, object]:
    """Build a compact, structured record for one rejected final candidate."""

    full_violations = [str(violation) for violation in violations]
    routes = candidate.van_routes if candidate.van_routes else {"van_0": candidate.van_route}
    sortie_modes = {
        (str(sortie.get("launch_van_id", "")), str(sortie.get("recovery_van_id", "")))
        for sortie in candidate.drone_sorties
        if isinstance(sortie, dict)
    }
    route_modes = {"cross-van" if launch != recovery else "same-van" for launch, recovery in sortie_modes}
    if not route_modes:
        same_van_or_cross_van = "none"
    elif len(route_modes) == 1:
        same_van_or_cross_van = next(iter(route_modes))
    else:
        same_van_or_cross_van = "mixed"
    categories = sorted({classify_violation(violation) for violation in full_violations})
    affected_customers = set(_affected_customers(full_violations, data))
    affected_vans = set(_affected_ids(full_violations, "van_"))
    affected_drones = set(_affected_ids(full_violations, "drone_"))
    for sortie in candidate.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        affected_customers.update(int(customer) for customer in sortie_nodes(sortie)[1])
        for field in ("launch_van_id", "recovery_van_id"):
            if sortie.get(field):
                affected_vans.add(str(sortie[field]))
        if sortie.get("drone_id"):
            affected_drones.add(str(sortie["drone_id"]))
    return {
        "iteration": int(iteration),
        "destroy_operator": str(destroy_operator),
        "repair_operator": str(repair_operator),
        "candidate_objective": float(candidate_objective),
        "number_of_unassigned_customers": int(len(candidate.unassigned)),
        "number_of_van_routes": int(len(routes)),
        "number_of_drone_sorties": int(len(candidate.drone_sorties)),
        "full_checker_violations": full_violations,
        "violation_categories": categories,
        "affected_customers": sorted(affected_customers),
        "affected_vans": sorted(affected_vans),
        "affected_drones": sorted(affected_drones),
        "same_van_or_cross_van": same_van_or_cross_van,
        "candidate_source": _candidate_source(repair_operator),
    }


def _route_signature(state: TVDState) -> Tuple[Tuple[str, Tuple[int, ...]], ...]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    return tuple(
        (str(van_id), tuple(int(node) for node in route))
        for van_id, route in sorted(routes.items())
    )


def drone_candidate_key(sortie: dict, state: TVDState) -> Tuple[object, ...]:
    launch, customers, recovery = sortie_nodes(sortie)
    return (
        str(sortie.get("drone_id", "")),
        str(sortie.get("launch_van_id", "")),
        int(launch),
        int(sortie.get("launch_position", -1)),
        str(sortie.get("recovery_van_id", sortie.get("launch_van_id", ""))),
        int(recovery),
        int(sortie.get("recovery_position", -1)),
        tuple(int(customer) for customer in customers),
        _route_signature(state),
    )


def _sortie_van_id(sortie: dict, field: str, fallback: str = "") -> str:
    return str(sortie.get(field, fallback) or fallback)


def _sortie_drone_id(sortie: dict) -> str:
    return str(sortie.get("drone_id", "") or "")


def _is_warehouse(state: TVDState, node: int) -> bool:
    return int(node) in {int(item) for item in state.transshipment_nodes}


def _positions_on_routes(sortie: dict, state: TVDState) -> List[str]:
    reasons: List[str] = []
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    launch, customers, recovery = sortie_nodes(sortie)
    launch_van = _sortie_van_id(sortie, "launch_van_id", sorted(routes)[0] if routes else "")
    recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
    launch_route = routes.get(launch_van)
    recovery_route = routes.get(recovery_van)
    launch_pos = int(sortie.get("launch_position", -1))
    recovery_pos = int(sortie.get("recovery_position", -1))

    if not customers:
        reasons.append("empty sortie")
    if launch_van not in routes:
        reasons.append("unknown launch_van")
    if recovery_van not in routes:
        reasons.append("unknown recovery_van")
    if launch_route is None or recovery_route is None:
        return reasons
    if not (0 <= launch_pos < len(launch_route) and int(launch_route[launch_pos]) == int(launch)):
        reasons.append("launch position does not match launch_van route")
    if not (
        0 <= recovery_pos < len(recovery_route)
        and int(recovery_route[recovery_pos]) == int(recovery)
    ):
        reasons.append("recovery position does not match recovery_van route")
    if launch_pos == len(launch_route) - 1:
        reasons.append("launch from terminal warehouse")
    if launch_van == recovery_van:
        if recovery_pos < launch_pos:
            reasons.append("recovery before launch on same van")
        if int(launch) == int(recovery) and recovery_pos != launch_pos:
            reasons.append("same-node launch/recovery at different positions")
    return reasons


def shadow_sortie_failures(sortie: dict, state: TVDState) -> List[str]:
    reasons = _positions_on_routes(sortie, state)
    drone_id = _sortie_drone_id(sortie)
    if drone_id and drone_id not in state.drone_initial_carrier:
        reasons.append("unknown physical drone")
    return reasons


def shadow_state_failures(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> List[Dict[str, object]]:
    """Conservative diagnostics for physical drone continuity.

    This is intentionally a shadow check: it reports reasons but never decides
    feasibility for production runs. Final feasibility remains owned by
    check_solution_feasible.
    """

    failures: List[Dict[str, object]] = []
    for idx, sortie in enumerate(state.drone_sorties):
        if not isinstance(sortie, dict):
            continue
        reasons = shadow_sortie_failures(sortie, state)
        if reasons:
            failures.append(
                {
                    "sortie_index": idx,
                    "drone_id": _sortie_drone_id(sortie),
                    "candidate_key": repr(drone_candidate_key(sortie, state)),
                    "reasons": reasons,
                    "sortie": dict(sortie),
                }
            )

    timing = compute_timing(state, data, config)
    physical_sorties = timing.get("drone_physical_sorties", {})
    if isinstance(physical_sorties, dict):
        for drone_id, records in physical_sorties.items():
            if not isinstance(records, list):
                continue
            previous = None
            for record_idx, record in enumerate(records):
                if not isinstance(record, dict):
                    continue
                reasons = []
                launch_van = str(record.get("launch_van_id", ""))
                recovery_van = str(record.get("recovery_van_id", launch_van))
                launch_pos = int(record.get("launch_position", -1))
                recovery_pos = int(record.get("recovery_position", -1))
                recovery_node = int(record.get("recovery_node", -1))
                if launch_pos < 0 or recovery_pos < 0:
                    reasons.append("unresolved launch/recovery position")
                if previous is None:
                    initial_carrier = str(state.drone_initial_carrier.get(str(drone_id), ""))
                    if initial_carrier and launch_van != initial_carrier:
                        reasons.append("first launch is not on physical drone initial carrier")
                else:
                    previous_recovery_van = str(previous.get("recovery_van_id", ""))
                    previous_recovery_node = int(previous.get("recovery_node", -1))
                    previous_recovery_time = float(previous.get("recovery_time", 0.0))
                    launch_time = float(record.get("launch_time", 0.0))
                    if launch_van != previous_recovery_van:
                        reasons.append("physical drone launches from a different carrier after recovery")
                    if launch_time + 1e-9 < previous_recovery_time:
                        reasons.append("physical drone launches before previous recovery time")
                    if _is_warehouse(state, previous_recovery_node):
                        reasons.append("physical drone continues after warehouse recovery")
                if _is_warehouse(state, recovery_node):
                    later = records[record_idx + 1 :]
                    if later:
                        reasons.append("physical drone continues after terminal warehouse return")
                if reasons:
                    failures.append(
                        {
                            "sortie_index": record_idx,
                            "drone_id": str(drone_id),
                            "candidate_key": repr(record),
                            "reasons": reasons,
                            "sortie": dict(record),
                        }
                    )
                previous = record

    launch_counts = timing.get("drone_warehouse_launch_count", {})
    if isinstance(launch_counts, dict):
        for drone_id, count in launch_counts.items():
            if int(count) > 1:
                failures.append(
                    {
                        "sortie_index": None,
                        "drone_id": str(drone_id),
                        "candidate_key": "",
                        "reasons": [f"duplicate warehouse departure count={int(count)}"],
                        "sortie": {},
                    }
                )
    return_counts = timing.get("drone_warehouse_return_count", {})
    if isinstance(return_counts, dict):
        for drone_id, count in return_counts.items():
            if int(count) > 1:
                failures.append(
                    {
                        "sortie_index": None,
                        "drone_id": str(drone_id),
                        "candidate_key": "",
                        "reasons": [f"duplicate warehouse return count={int(count)}"],
                        "sortie": {},
                    }
                )

    high_floor_unassigned = [
        int(customer)
        for customer, high_floor in data.is_high_floor.items()
        if high_floor and state.service_mode.get(int(customer)) != "drone"
    ]
    if high_floor_unassigned:
        failures.append(
            {
                "sortie_index": None,
                "drone_id": "",
                "candidate_key": "",
                "reasons": ["unassigned high-floor customer"],
                "customers": high_floor_unassigned,
                "sortie": {},
            }
        )
    return failures


def summarize_failure_reasons(failures: Iterable[Dict[str, object]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for failure in failures:
        for reason in failure.get("reasons", []):
            counts[str(reason)] += 1
    return dict(counts)
