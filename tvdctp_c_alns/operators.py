from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

from alns_profile import (
    active_repair_name,
    enter_repair,
    exit_repair,
    add_local_feasibility_eval_time,
    get_local_feasibility_cache,
    increment,
    record_local_drone_candidate,
    record_destroy_result,
    record_repair_candidate,
    record_repair_rejection,
    set_local_feasibility_cache,
)
from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import (
    check_solution_feasible,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_peak_payload,
    sortie_nodes,
)
from objective import objective
from removal_structural_context import (
    attach_active_removal_context,
    capture_structural_projection,
    discard_active_removal_context,
    finalize_removal_structural_context,
    removal_context_boundary,
)
from state import (
    AffectedStructureScope,
    CarrierTransferSnapshot,
    CascadeBundleSnapshot,
    ContainerDecisionSnapshot,
    CustomerServiceSnapshot,
    DroneSubrouteSnapshot,
    LaunchRecoverySnapshot,
    TruckWarehouseContextSnapshot,
    TVDState,
    VanRoutePositionSnapshot,
    VanRouteSegmentSnapshot,
    default_timing,
)


DestroyOperator = Callable[[TVDState, np.random.Generator, InstanceData, TVDConfig], TVDState]
RepairOperator = Callable[[TVDState, np.random.Generator, InstanceData, TVDConfig], TVDState]

CASCADE_CONTRACT_SCHEMA_VERSION = 1
CASCADE_SOURCE_OPERATOR = "cascade_aware_removal"
CASCADE_METADATA_KEYS = (
    "cascade_removed",
    "cascade_bundles",
    "cascade_contract",
)


@dataclass
class InsertionMove:
    mode: str
    cost: float
    index: Optional[int] = None
    van_id: Optional[str] = None
    sortie: Optional[dict] = None


@dataclass
class RegretEvaluation:
    customer: int
    moves: List[InsertionMove]
    best_move: InsertionMove
    second_move: Optional[InsertionMove]
    regret: Optional[float]
    original_order: int
    raw_candidate_count: int
    van_candidate_count: int
    drone_candidate_count: int
    enumeration_seconds: float
    ranking_seconds: float


@dataclass
class BundleReconstructionStrategy:
    """One complete, atomic reconstruction candidate for a Cascade bundle.

    Implementation choice: the paper does not explicitly specify the concrete
    construction of Ω(B).  This identity describes the complete reconstructed
    bundle and affected structures; it never uses objective cost for identity
    or deduplication.
    """

    bundle_id: str
    customer_ids: Tuple[int, ...]
    service_mode_reconstruction: Tuple[Tuple[int, str], ...]
    van_route_segment_reconstruction: Tuple[Tuple[str, Tuple[int, ...]], ...]
    drone_subroute_reconstruction: Tuple[Tuple[object, ...], ...]
    launch_recovery_reconstruction: Tuple[Tuple[object, ...], ...]
    carrier_transfer_reconstruction: Tuple[Tuple[object, ...], ...]
    coordination_links: Tuple[str, ...]
    resulting_state: TVDState = field(repr=False, compare=False)
    source_kind: str = field(default="", compare=False)
    objective_value: Optional[float] = field(default=None, compare=False)

    def stable_identity(self) -> Tuple[object, ...]:
        return (
            self.bundle_id,
            self.customer_ids,
            self.service_mode_reconstruction,
            self.van_route_segment_reconstruction,
            self.drone_subroute_reconstruction,
            self.launch_recovery_reconstruction,
            self.carrier_transfer_reconstruction,
            self.coordination_links,
        )


def _removal_count(data: InstanceData, config: TVDConfig) -> int:
    return max(1, int(round(len(data.customers) * config.alns.customer_removal_ratio)))


def _served_customers(state: TVDState) -> List[int]:
    return sorted(set(state.get_van_customers() + state.get_drone_customers()))


def _clear_stale_cascade_metadata(state: TVDState) -> None:
    for key in CASCADE_METADATA_KEYS:
        state.metadata.pop(key, None)
    discard_active_removal_context(state)


def _state_business_fingerprint(state: TVDState) -> str:
    payload = repr(state.cache_signature()).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cascade_metadata_is_current(state: TVDState) -> bool:
    """Return whether Cascade metadata describes this exact destroyed State.

    Stage 2D.0 establishes this validator for the future Stage 2D.1 reader; it
    intentionally does not change the current ``cascade_repair`` algorithm.
    """

    contract = state.metadata.get("cascade_contract")
    bundles = state.metadata.get("cascade_bundles")
    if not isinstance(contract, dict) or not isinstance(bundles, list):
        return False
    if contract.get("schema_version") != CASCADE_CONTRACT_SCHEMA_VERSION:
        return False
    if contract.get("source_operator") != CASCADE_SOURCE_OPERATOR:
        return False
    if contract.get("destroyed_state_fingerprint") != _state_business_fingerprint(state):
        return False
    if not all(isinstance(bundle, CascadeBundleSnapshot) for bundle in bundles):
        return False
    bundle_ids = tuple(bundle.bundle_id for bundle in bundles)
    bundle_fingerprints = tuple(bundle.contract_fingerprint() for bundle in bundles)
    return (
        bundle_ids == tuple(contract.get("bundle_ids", ()))
        and bundle_fingerprints == tuple(contract.get("bundle_fingerprints", ()))
        and all(
            bundle.source_destroy_call_id == contract.get("destroy_call_id")
            and bundle.source_state_fingerprint == contract.get("source_state_fingerprint")
            for bundle in bundles
        )
    )


def _record_destroy_diagnostics(
    state: TVDState,
    customers: Iterable[int],
    data: InstanceData,
    *,
    cascade_expansion_count: int = 0,
) -> None:
    selected = sorted({int(customer) for customer in customers})
    drone_customers = set(state.get_drone_customers())
    van_customers = set(state.get_van_customers())
    record_destroy_result(
        removed_customers=selected,
        high_floor_customers=[
            customer for customer in selected if data.is_high_floor.get(customer, False)
        ],
        drone_customers=[customer for customer in selected if customer in drone_customers],
        van_customers=[customer for customer in selected if customer in van_customers],
        cascade_expansion_count=cascade_expansion_count,
    )


def _remove_customer(state: TVDState, customer: int) -> None:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for van_id, route in list(routes.items()):
        if customer in route:
            routes[van_id] = [node for node in route if node != customer]
    state.van_routes = routes
    state.sync_primary_van_route()

    remaining_sorties = []
    removed_drone_customers = set()
    for sortie in state.drone_sorties:
        launch, sortie_customers, recovery = sortie_nodes(sortie)
        if customer in sortie_customers or customer in (launch, recovery):
            removed_drone_customers.update(sortie_customers)
        else:
            remaining_sorties.append(sortie)
    state.drone_sorties = remaining_sorties

    for removed_customer in sorted(removed_drone_customers | {customer}):
        state.mark_unassigned(removed_customer)


def _remove_customers(
    state: TVDState,
    customers: Iterable[int],
    *,
    deletion_attempt_order: Optional[List[int]] = None,
    actual_unassignment_order: Optional[List[int]] = None,
) -> TVDState:
    for customer in customers:
        normalized = int(customer)
        if deletion_attempt_order is not None:
            deletion_attempt_order.append(normalized)
        before_unassigned = set(int(item) for item in state.unassigned)
        _remove_customer(state, normalized)
        if actual_unassignment_order is not None:
            actual_unassignment_order.extend(
                int(item)
                for item in state.unassigned
                if int(item) not in before_unassigned
                and int(item) not in actual_unassignment_order
            )
    return state


def _attach_removal_structural_context(
    destroyed: TVDState,
    *,
    pre_projection,
    source_destroy_operator: str,
    selected_removed_customer_ids: Iterable[int],
    customer_selection_order: Iterable[int],
    deletion_attempt_order: Iterable[int],
    actual_unassignment_order: Iterable[int],
    cascade_dependency_trace: Iterable[Tuple[int, int]] = (),
    cascade_native_partition_evidence: Iterable[Iterable[int]] = (),
    cascade_native_dependency_order: Iterable[Iterable[int]] = (),
) -> TVDState:
    context = finalize_removal_structural_context(
        pre_projection=pre_projection,
        post_projection=capture_structural_projection(destroyed),
        source_destroy_operator=source_destroy_operator,
        selected_removed_customer_ids=selected_removed_customer_ids,
        customer_selection_order=customer_selection_order,
        deletion_attempt_order=deletion_attempt_order,
        actual_unassignment_order=actual_unassignment_order,
        cascade_dependency_trace=cascade_dependency_trace,
        cascade_native_partition_evidence=cascade_native_partition_evidence,
        cascade_native_dependency_order=cascade_native_dependency_order,
    )
    return attach_active_removal_context(destroyed, context)


def _remove_duplicate_unassigned(state: TVDState) -> None:
    seen = set()
    cleaned = []
    for customer in state.unassigned:
        if customer not in seen:
            cleaned.append(customer)
            seen.add(customer)
    state.unassigned = cleaned


def random_customer_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    _clear_stale_cascade_metadata(destroyed)
    pre_projection = capture_structural_projection(destroyed)
    served = _served_customers(destroyed)
    count = min(_removal_count(data, config), len(served))
    selected = rng.choice(served, size=count, replace=False).tolist() if served else []
    _record_destroy_diagnostics(destroyed, selected, data)
    deletion_order: List[int] = []
    actual_order: List[int] = []
    _remove_customers(
        destroyed,
        selected,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )
    return _attach_removal_structural_context(
        destroyed,
        pre_projection=pre_projection,
        source_destroy_operator="random_customer_removal",
        selected_removed_customer_ids=selected,
        customer_selection_order=selected,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )


def greedy_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    """论文 greedy removal：删除边际贡献最大的客户。"""

    destroyed = state.copy()
    _clear_stale_cascade_metadata(destroyed)
    pre_projection = capture_structural_projection(destroyed)
    base_cost, _ = objective(destroyed.copy(), data, config)
    scores: List[Tuple[float, int]] = []
    for customer in _served_customers(destroyed):
        trial = destroyed.copy()
        _remove_customer(trial, customer)
        trial.clean_unassigned(customer)
        trial_cost, _ = objective(trial, data, config)
        scores.append((base_cost - trial_cost, customer))

    count = min(_removal_count(data, config), len(scores))
    selected = [customer for _, customer in sorted(scores, reverse=True)[:count]]
    _record_destroy_diagnostics(destroyed, selected, data)
    deletion_order: List[int] = []
    actual_order: List[int] = []
    _remove_customers(
        destroyed,
        selected,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )
    return _attach_removal_structural_context(
        destroyed,
        pre_projection=pre_projection,
        source_destroy_operator="greedy_removal",
        selected_removed_customer_ids=selected,
        customer_selection_order=selected,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )


def related_customer_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    _clear_stale_cascade_metadata(destroyed)
    pre_projection = capture_structural_projection(destroyed)
    served = _served_customers(destroyed)
    if not served:
        return _attach_removal_structural_context(
            destroyed,
            pre_projection=pre_projection,
            source_destroy_operator="related_customer_removal",
            selected_removed_customer_ids=(),
            customer_selection_order=(),
            deletion_attempt_order=(),
            actual_unassignment_order=(),
        )

    seed = int(rng.choice(served))
    count = min(_removal_count(data, config), len(served))
    selected = sorted(
        served, key=lambda customer: data.ground_distance_matrix[seed, customer]
    )[:count]
    _record_destroy_diagnostics(destroyed, selected, data)
    deletion_order: List[int] = []
    actual_order: List[int] = []
    _remove_customers(
        destroyed,
        selected,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )
    return _attach_removal_structural_context(
        destroyed,
        pre_projection=pre_projection,
        source_destroy_operator="related_customer_removal",
        selected_removed_customer_ids=selected,
        customer_selection_order=(seed,),
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )


def route_segment_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    _clear_stale_cascade_metadata(destroyed)
    internal = destroyed.get_van_customers()
    if not internal:
        return random_customer_removal(destroyed, rng, data, config)

    count = min(_removal_count(data, config), len(internal))
    start = int(rng.integers(0, len(internal) - count + 1))
    selected = internal[start : start + count]
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def drone_task_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    _clear_stale_cascade_metadata(destroyed)
    if not destroyed.drone_sorties:
        return random_customer_removal(destroyed, rng, data, config)

    count = min(_removal_count(data, config), len(destroyed.drone_sorties))
    selected_idx = rng.choice(range(len(destroyed.drone_sorties)), size=count, replace=False)
    selected = []
    for idx in selected_idx:
        _, sortie_customers, _ = sortie_nodes(destroyed.drone_sorties[int(idx)])
        selected.extend(sortie_customers)
    _record_destroy_diagnostics(destroyed, selected, data)
    return _remove_customers(destroyed, selected)


def _cascade_dependencies(state: TVDState, customer: int) -> set[int]:
    deps = {customer}
    for sortie in state.drone_sorties:
        launch, drone_customers, recovery = sortie_nodes(sortie)
        if customer in [launch, recovery] + drone_customers:
            deps.update(drone_customers)
            if launch not in state.metadata.get("route_endpoints", []):
                deps.add(launch)
            if recovery not in state.metadata.get("route_endpoints", []):
                deps.add(recovery)
    return deps


def _optional_int(value: object) -> Optional[int]:
    return None if value is None else int(value)


def _optional_float(value: object) -> Optional[float]:
    return None if value is None else float(value)


def _optional_str(value: object) -> Optional[str]:
    return None if value is None else str(value)


def _cascade_destroy_call_id(
    source_state_fingerprint: str,
    initial: Iterable[int],
    removal: Iterable[int],
    bundles: Iterable[Iterable[int]],
) -> str:
    payload = (
        CASCADE_CONTRACT_SCHEMA_VERSION,
        CASCADE_SOURCE_OPERATOR,
        source_state_fingerprint,
        tuple(int(customer) for customer in initial),
        tuple(sorted(int(customer) for customer in removal)),
        tuple(tuple(int(customer) for customer in bundle) for bundle in bundles),
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _capture_cascade_bundle_snapshot(
    state: TVDState,
    bundle: Iterable[int],
    *,
    bundle_index: int,
    source_state_fingerprint: str,
    destroy_call_id: str,
    data: InstanceData,
) -> CascadeBundleSnapshot:
    customer_ids = tuple(int(customer) for customer in bundle)
    customer_set = set(customer_ids)

    service_snapshots = []
    affected_van_ids = set()
    affected_nodes = set(customer_ids)
    affected_container_ids = set()
    for customer in customer_ids:
        positions = []
        for van_id, route in sorted(state.van_routes.items()):
            for route_position, node in enumerate(route):
                if int(node) == customer:
                    affected_van_ids.add(str(van_id))
                    positions.append(
                        VanRoutePositionSnapshot(
                            van_id=str(van_id),
                            route_position=route_position,
                            warehouse_id=_optional_int(state.van_home.get(str(van_id))),
                        )
                    )
        assignment = state.order_assignment.get(customer, {})
        container_id = _optional_int(assignment.get("container_id"))
        if container_id is not None:
            affected_container_ids.add(container_id)
        service_snapshots.append(
            CustomerServiceSnapshot(
                customer_id=customer,
                service_mode=_optional_str(state.service_mode.get(customer)),
                van_route_positions=tuple(positions),
                container_id=container_id,
                assigned_transshipment=_optional_int(
                    assignment.get("assigned_transshipment")
                ),
            )
        )

    drone_subroutes = []
    launch_recovery_snapshots = []
    carrier_snapshots = []
    for sortie_index, sortie in enumerate(state.drone_sorties):
        launch, sortie_customers, recovery = sortie_nodes(sortie)
        related = set(int(customer) for customer in sortie_customers)
        if launch in data.customers:
            related.add(int(launch))
        if recovery in data.customers:
            related.add(int(recovery))
        if not customer_set.intersection(related):
            continue

        sortie_id = f"sortie:{sortie_index}"
        sortie_dict = sortie if isinstance(sortie, dict) else {}
        drone_id = _optional_str(sortie_dict.get("drone_id"))
        launch_van_id = _optional_str(sortie_dict.get("launch_van_id"))
        recovery_van_id = _optional_str(sortie_dict.get("recovery_van_id"))
        launch_position = _optional_int(sortie_dict.get("launch_position"))
        recovery_position = _optional_int(sortie_dict.get("recovery_position"))
        same_van_recovery = (
            launch_van_id == recovery_van_id
            if launch_van_id is not None and recovery_van_id is not None
            else None
        )
        carrier_transfer = (
            launch_van_id != recovery_van_id
            if launch_van_id is not None and recovery_van_id is not None
            else None
        )
        initial_carrier = (
            _optional_str(state.drone_initial_carrier.get(drone_id))
            if drone_id is not None
            else None
        )

        affected_nodes.update((int(launch), int(recovery)))
        if launch_van_id is not None:
            affected_van_ids.add(launch_van_id)
        if recovery_van_id is not None:
            affected_van_ids.add(recovery_van_id)
        drone_subroutes.append(
            DroneSubrouteSnapshot(
                sortie_id=sortie_id,
                source_sortie_index=sortie_index,
                drone_id=drone_id,
                customer_ids=tuple(int(customer) for customer in sortie_customers),
                launch_node=int(launch),
                recovery_node=int(recovery),
            )
        )
        launch_recovery_snapshots.append(
            LaunchRecoverySnapshot(
                sortie_id=sortie_id,
                launch_van_id=launch_van_id,
                recovery_van_id=recovery_van_id,
                launch_node=int(launch),
                recovery_node=int(recovery),
                launch_position=launch_position,
                recovery_position=recovery_position,
                same_van_recovery=same_van_recovery,
            )
        )
        carrier_snapshots.append(
            CarrierTransferSnapshot(
                sortie_id=sortie_id,
                drone_id=drone_id,
                initial_carrier_van_id=initial_carrier,
                launch_carrier_van_id=launch_van_id,
                recovery_carrier_van_id=recovery_van_id,
                carrier_transfer=carrier_transfer,
            )
        )

    route_segments = []
    route_segment_ids = []
    for van_id in sorted(affected_van_ids):
        route = state.van_routes.get(van_id, [])
        affected_positions = tuple(
            position
            for position, node in enumerate(route)
            if int(node) in affected_nodes
        )
        if affected_positions:
            start_position = max(0, min(affected_positions) - 1)
            end_position = min(len(route) - 1, max(affected_positions) + 1)
            route_nodes = tuple(
                int(node) for node in route[start_position : end_position + 1]
            )
            route_segment_id = f"van:{van_id}:{start_position}-{end_position}"
        else:
            start_position = -1
            end_position = -1
            route_nodes = ()
            route_segment_id = f"van:{van_id}:unresolved"
        route_segments.append(
            VanRouteSegmentSnapshot(
                van_id=van_id,
                warehouse_id=_optional_int(state.van_home.get(van_id)),
                start_position=start_position,
                end_position=end_position,
                route_nodes=route_nodes,
                affected_positions=affected_positions,
            )
        )
        route_segment_ids.append(route_segment_id)

    container_decisions = []
    for container_id in sorted(affected_container_ids):
        route = state.container_routes.get(container_id, {})
        container_decisions.append(
            ContainerDecisionSnapshot(
                container_id=container_id,
                origin_node=_optional_int(route.get("origin")),
                destination_warehouse=_optional_int(
                    route.get("destination_warehouse")
                ),
                tractor_id=_optional_str(route.get("tractor_id")),
                trailer_id=_optional_str(route.get("trailer_id")),
                unload_complete=_optional_float(route.get("unload_complete")),
            )
        )

    drone_subroute_ids = tuple(snapshot.sortie_id for snapshot in drone_subroutes)
    launch_recovery_ids = tuple(
        edge_id
        for snapshot in launch_recovery_snapshots
        for edge_id in (
            f"{snapshot.sortie_id}:launch",
            f"{snapshot.sortie_id}:recovery",
        )
    )
    carrier_link_ids = tuple(
        f"{snapshot.sortie_id}:carrier" for snapshot in carrier_snapshots
    )
    coordination_edge_ids = tuple(
        edge_id
        for snapshot in launch_recovery_snapshots
        for edge_id in (
            f"{snapshot.sortie_id}:truck-van-context",
            f"{snapshot.sortie_id}:van-drone-launch",
            f"{snapshot.sortie_id}:van-drone-recovery",
        )
    )
    truck_context_ids = (
        f"selected_transshipment:{int(state.selected_transshipment)}",
        *(f"container:{container_id}" for container_id in sorted(affected_container_ids)),
    )
    scope = AffectedStructureScope(
        truck_context_ids=truck_context_ids,
        van_route_segment_ids=tuple(route_segment_ids),
        drone_subroute_ids=drone_subroute_ids,
        launch_recovery_link_ids=launch_recovery_ids,
        carrier_link_ids=carrier_link_ids,
        coordination_edge_ids=coordination_edge_ids,
    )
    return CascadeBundleSnapshot(
        schema_version=CASCADE_CONTRACT_SCHEMA_VERSION,
        bundle_id=f"cascade:{destroy_call_id[:20]}:bundle:{bundle_index:04d}",
        source_operator=CASCADE_SOURCE_OPERATOR,
        source_destroy_call_id=destroy_call_id,
        source_state_fingerprint=source_state_fingerprint,
        customer_ids=customer_ids,
        dependency_order=customer_ids,
        dependency_order_semantics="current implementation order; Paper unspecified",
        customer_service_snapshots=tuple(service_snapshots),
        affected_route_segments=tuple(route_segments),
        removed_drone_subroutes=tuple(drone_subroutes),
        launch_recovery_snapshots=tuple(launch_recovery_snapshots),
        carrier_transfer_snapshots=tuple(carrier_snapshots),
        truck_warehouse_context=TruckWarehouseContextSnapshot(
            selected_transshipment=int(state.selected_transshipment),
            container_decisions=tuple(container_decisions),
        ),
        affected_structure_scope=scope,
    )


def cascade_aware_removal(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    destroyed = state.copy()
    _clear_stale_cascade_metadata(destroyed)
    pre_projection = capture_structural_projection(destroyed)
    source_state_fingerprint = _state_business_fingerprint(destroyed)
    served = _served_customers(destroyed)
    count = min(_removal_count(data, config), len(served))
    initial = rng.choice(served, size=count, replace=False).tolist() if served else []
    removal = set(initial)
    dependency_trace: List[Tuple[int, int]] = []

    changed = True
    while changed:
        changed = False
        for customer in list(removal):
            deps = _cascade_dependencies(destroyed, customer)
            dependency_trace.extend(
                (int(customer), int(dependency))
                for dependency in sorted(deps - removal)
            )
            if not deps.issubset(removal):
                removal |= deps
                changed = True

    bundles = []
    assigned = set()
    for sortie in destroyed.drone_sorties:
        launch, drone_customers, recovery = sortie_nodes(sortie)
        related = set(drone_customers)
        if launch in data.customers:
            related.add(launch)
        if recovery in data.customers:
            related.add(recovery)
        bundle = sorted(related & removal)
        if bundle:
            bundles.append(bundle)
            assigned.update(bundle)
    for customer in sorted(removal - assigned):
        bundles.append([customer])

    destroy_call_id = _cascade_destroy_call_id(
        source_state_fingerprint,
        initial,
        removal,
        bundles,
    )
    bundle_snapshots = [
        _capture_cascade_bundle_snapshot(
            destroyed,
            bundle,
            bundle_index=bundle_index,
            source_state_fingerprint=source_state_fingerprint,
            destroy_call_id=destroy_call_id,
            data=data,
        )
        for bundle_index, bundle in enumerate(bundles)
    ]

    _record_destroy_diagnostics(
        destroyed,
        removal,
        data,
        cascade_expansion_count=max(0, len(removal) - len(initial)),
    )
    deletion_order: List[int] = []
    actual_order: List[int] = []
    destroyed = _remove_customers(
        destroyed,
        removal,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
    )
    _remove_duplicate_unassigned(destroyed)
    destroyed_state_fingerprint = _state_business_fingerprint(destroyed)
    destroyed.metadata["cascade_removed"] = sorted(removal)
    destroyed.metadata["cascade_bundles"] = bundle_snapshots
    destroyed.metadata["cascade_contract"] = {
        "schema_version": CASCADE_CONTRACT_SCHEMA_VERSION,
        "source_operator": CASCADE_SOURCE_OPERATOR,
        "destroy_call_id": destroy_call_id,
        "source_state_fingerprint": source_state_fingerprint,
        "destroyed_state_fingerprint": destroyed_state_fingerprint,
        "bundle_ids": tuple(bundle.bundle_id for bundle in bundle_snapshots),
        "bundle_fingerprints": tuple(
            bundle.contract_fingerprint() for bundle in bundle_snapshots
        ),
        "captured_before_removal": True,
    }
    return _attach_removal_structural_context(
        destroyed,
        pre_projection=pre_projection,
        source_destroy_operator=CASCADE_SOURCE_OPERATOR,
        selected_removed_customer_ids=removal,
        customer_selection_order=initial,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
        cascade_dependency_trace=dependency_trace,
        cascade_native_partition_evidence=(
            bundle.customer_ids for bundle in bundle_snapshots
        ),
        cascade_native_dependency_order=(
            bundle.dependency_order for bundle in bundle_snapshots
        ),
    )


def _truck_route_for_transshipment(data: InstanceData, selected_transshipment: int) -> List[int]:
    if data.container_origin == selected_transshipment:
        return [data.truck_depot_node, selected_transshipment]
    return [data.truck_depot_node, data.container_origin, selected_transshipment]


def _rebuild_assignments_for_transshipment(
    state: TVDState, data: InstanceData, selected_transshipment: int
) -> None:
    for assignment in state.order_assignment.values():
        container_id = int(assignment.get("container_id", -1))
        container_route = state.container_routes.get(container_id, {})
        assignment["assigned_transshipment"] = int(
            container_route.get("destination_warehouse", selected_transshipment)
        )

    for container_id, assignment in state.container_assignment.items():
        container_route = state.container_routes.get(int(container_id), {})
        destination = int(container_route.get("destination_warehouse", selected_transshipment))
        assignment["origin_node"] = data.container_origin
        assignment["candidate_transshipments"] = data.transshipment_nodes.copy()
        assignment["selected_transshipment"] = destination
        assignment["destination_warehouse"] = destination


def switch_transshipment_operator(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    """Move the solution to another candidate warehouse, then let repair rebuild service."""

    switched = state.copy()
    _clear_stale_cascade_metadata(switched)
    alternatives = [
        node
        for node in data.transshipment_nodes
        if node != switched.selected_transshipment
    ]
    if not alternatives:
        return switched

    new_transshipment = int(rng.choice(alternatives))
    old_transshipment = switched.selected_transshipment
    from initial_solution import _build_stage1_drayage

    destinations = {
        int(container_id): new_transshipment
        for container_id in data.container_assignment
    }
    (
        tractor_routes,
        container_routes,
        tractor_home,
        trailer_home,
        truck_route,
        warehouse_ready_time,
    ) = _build_stage1_drayage(data, config, destinations)
    switched.selected_transshipment = new_transshipment
    switched.truck_route = truck_route
    switched.tractor_routes = tractor_routes
    switched.tractor_home = tractor_home
    switched.trailer_home = trailer_home
    switched.container_routes = container_routes
    van_home = config.build_van_home(data.transshipment_nodes)
    drone_initial_carrier = config.build_drone_initial_carrier(data.transshipment_nodes)
    drone_home_warehouse = config.build_drone_home_warehouse(data.transshipment_nodes)
    switched.van_home = van_home
    switched.drone_initial_carrier = drone_initial_carrier
    switched.drone_home_warehouse = drone_home_warehouse
    switched.van_routes = {
        van_id: [new_transshipment, new_transshipment]
        for van_id, home in van_home.items()
        if int(home) == int(new_transshipment)
    }
    switched.sync_primary_van_route()
    switched.drone_sorties = []
    _record_destroy_diagnostics(state, data.customers, data)
    switched.unassigned = data.customers.copy()
    switched.service_mode = {customer: "unassigned" for customer in data.customers}
    switched.metadata["route_endpoints"] = sorted(set(data.transshipment_nodes))
    switched.metadata["warehouse_num_vans"] = config.warehouse_num_vans(data.transshipment_nodes)
    switched.metadata["warehouse_num_drones"] = config.warehouse_num_drones(data.transshipment_nodes)
    switched.metadata["drones_per_van"] = config.fleet.drones_per_van
    switched.metadata["warehouse_ready_time"] = warehouse_ready_time
    switched.metadata["transshipment_switched_from"] = old_transshipment
    switched.metadata["transshipment_switched_to"] = new_transshipment
    switched.timing = default_timing()
    _rebuild_assignments_for_transshipment(switched, data, new_transshipment)
    return switched


def _van_insert_cost(customer: int, route: List[int], idx: int, data: InstanceData) -> float:
    pred = route[idx - 1]
    succ = route[idx]
    dist = data.ground_distance_matrix
    return float(dist[pred, customer] + dist[customer, succ] - dist[pred, succ])


def _can_van_insert(
    customer: int,
    route: List[int],
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    route_customers = [node for node in route if node in data.customers]
    current_delivery = sum(data.demands[c] for c in route_customers)
    current_pickup = sum(getattr(data, "pickup_demands", {}).get(c, 0.0) for c in route_customers)
    customer_pickup = getattr(data, "pickup_demands", {}).get(customer, 0.0)
    return current_delivery + current_pickup + data.demands[customer] + customer_pickup <= config.fleet.van_capacity_kg


def _travel_minutes(distance: float, speed_kmph: float) -> float:
    return float(distance) / speed_kmph * 60.0


def _route_payload(route: List[int], data: InstanceData) -> float:
    return float(
        sum(float(data.demands.get(node, 0.0)) for node in route if node in data.customers)
        + sum(
            float(getattr(data, "pickup_demands", {}).get(node, 0.0))
            for node in route
            if node in data.customers
        )
    )


def _warehouse_ready_times(state: TVDState) -> Dict[int, float]:
    ready = {
        int(warehouse): float(ready_time)
        for warehouse, ready_time in state.metadata.get("warehouse_ready_time", {}).items()
    }
    for container in getattr(state, "container_routes", {}).values():
        if not isinstance(container, dict):
            continue
        warehouse = int(container.get("destination_warehouse", state.selected_transshipment))
        ready[warehouse] = max(ready.get(warehouse, 0.0), float(container.get("unload_complete", 0.0)))
    return ready


def _van_route_timing_feasible(
    route: List[int],
    start_time: float,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    if len(route) < 2:
        return False
    current_time = float(start_time)
    previous = int(route[0])
    for idx, node in enumerate(route):
        node = int(node)
        if idx > 0:
            current_time += _travel_minutes(
                data.ground_distance_matrix[previous, node],
                config.fleet.van_speed_kmph,
            )
        if node in data.customers:
            earliest, latest = data.time_windows.get(node, (0.0, float("inf")))
            service_start = max(current_time, float(earliest))
            if service_start > float(latest) + 1e-9:
                return False
            current_time = service_start + float(data.service_times.get(node, 0.0))
        previous = node
    return True


def _route_service_time_at_position(
    route: List[int],
    position: int,
    start_time: float,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[float]:
    if not route or position < 0 or position >= len(route):
        return None
    current_time = float(start_time)
    previous = int(route[0])
    for idx, node in enumerate(route):
        node = int(node)
        if idx > 0:
            current_time += _travel_minutes(
                data.ground_distance_matrix[previous, node],
                config.fleet.van_speed_kmph,
            )
        if node in data.customers:
            earliest, latest = data.time_windows.get(node, (0.0, float("inf")))
            service_start = max(current_time, float(earliest))
            if service_start > float(latest) + 1e-9:
                return None
            current_time = service_start + float(data.service_times.get(node, 0.0))
        if idx == position:
            return float(current_time)
        previous = node
    return None


def _repair_van_routes(state: TVDState) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    repaired = {str(van_id): route.copy() for van_id, route in routes.items()}
    selected = int(state.selected_transshipment)
    for van_id, home in sorted(state.van_home.items(), key=lambda item: int(item[0].split("_")[1])):
        if int(home) == selected and van_id not in repaired:
            repaired[van_id] = [selected, selected]
    return repaired


def _is_allowed_partial_repair_violation(violation: str, state: TVDState) -> bool:
    if violation.startswith("unassigned customers remain:"):
        return True
    prefix = "high-floor customer "
    if violation.startswith(prefix) and " must be served by drone." in violation:
        try:
            customer = int(violation[len(prefix):].split()[0])
        except (IndexError, ValueError):
            return False
        return customer in state.unassigned
    return False


def _partial_repair_hard_feasible(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    feasible, violations = check_solution_feasible(state, data, config)
    return feasible or all(
        _is_allowed_partial_repair_violation(str(violation), state)
        for violation in violations
    )


def _van_insert_hard_feasible(
    customer: int,
    van_id: str,
    candidate_route: List[int],
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    if data.is_high_floor.get(int(customer), False):
        record_repair_rejection("van_high_floor")
        return False
    if _route_payload(candidate_route, data) > config.fleet.van_capacity_kg + 1e-9:
        record_repair_rejection("rejected_by_capacity")
        return False
    if not candidate_route or int(candidate_route[0]) not in state.transshipment_nodes:
        record_repair_rejection("van_bad_route_endpoint")
        return False
    if int(candidate_route[-1]) not in state.transshipment_nodes:
        record_repair_rejection("van_bad_route_endpoint")
        return False
    start_time = _warehouse_ready_times(state).get(int(candidate_route[0]), 0.0)
    feasible = _van_route_timing_feasible(candidate_route, start_time, data, config)
    if not feasible:
        record_repair_rejection("rejected_by_time_window")
    return feasible


def _drone_route_signature(state: TVDState) -> Tuple[Tuple[str, Tuple[int, ...]], ...]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    return tuple(
        (str(van_id), tuple(int(node) for node in route))
        for van_id, route in sorted(routes.items())
    )


def _existing_drone_sortie_signature(state: TVDState) -> Tuple[Tuple[object, ...], ...]:
    result = []
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            result.append(tuple(sortie))  # type: ignore[arg-type]
            continue
        launch, customers, recovery = sortie_nodes(sortie)
        result.append(
            (
                str(sortie.get("drone_id", "")),
                str(sortie.get("launch_van_id", "")),
                int(launch),
                int(sortie.get("launch_position", -1)),
                str(sortie.get("recovery_van_id", sortie.get("launch_van_id", ""))),
                int(recovery),
                int(sortie.get("recovery_position", -1)),
                tuple(int(customer) for customer in customers),
            )
        )
    return tuple(result)


def _warehouse_ready_signature(state: TVDState) -> Tuple[Tuple[int, float], ...]:
    ready = _warehouse_ready_times(state)
    return tuple(
        (int(warehouse), round(float(ready_time), 9))
        for warehouse, ready_time in sorted(ready.items())
    )


def _container_assignment_signature(state: TVDState) -> Tuple[Tuple[object, ...], ...]:
    return tuple(
        (
            int(customer),
            int(assignment.get("container_id", -1)),
            int(assignment.get("assigned_transshipment", -1)),
        )
        for customer, assignment in sorted(state.order_assignment.items())
    )


def _container_destination_signature(state: TVDState) -> Tuple[Tuple[object, ...], ...]:
    return tuple(
        (
            int(container_id),
            int(route.get("destination_warehouse", -1)),
            round(float(route.get("unload_complete", 0.0)), 9),
            tuple(int(customer) for customer in route.get("customers", [])),
        )
        for container_id, route in sorted(state.container_routes.items())
    )


def _drone_local_feasibility_cache_key(
    customers: List[int],
    sortie: dict,
    state: TVDState,
) -> Tuple[object, ...]:
    launch, sortie_customers, recovery = sortie_nodes(sortie)
    return (
        id(state),
        str(sortie.get("drone_id", "")),
        str(sortie.get("launch_van_id", "")),
        int(launch),
        int(sortie.get("launch_position", -1)),
        str(sortie.get("recovery_van_id", sortie.get("launch_van_id", ""))),
        int(recovery),
        int(sortie.get("recovery_position", -1)),
        tuple(int(customer) for customer in sortie_customers or customers),
        _drone_route_signature(state),
        _existing_drone_sortie_signature(state),
        tuple((int(customer), str(mode)) for customer, mode in sorted(state.service_mode.items())),
        tuple(int(customer) for customer in state.unassigned),
        _warehouse_ready_signature(state),
        _container_assignment_signature(state),
        _container_destination_signature(state),
    )


def _route_position_time_from_state(
    state: TVDState,
    van_id: str,
    route: List[int],
    position: int,
    field: str,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[float]:
    sequences_by_van = state.timing.get("van_arrival_sequence_by_van", {})
    if isinstance(sequences_by_van, dict):
        sequence = sequences_by_van.get(str(van_id), [])
        if isinstance(sequence, list) and len(sequence) == len(route):
            if all(
                isinstance(entry, dict) and int(entry.get("node", -1)) == int(node)
                for entry, node in zip(sequence, route)
            ):
                entry = sequence[position]
                if isinstance(entry, dict) and field in entry:
                    return float(entry[field])

    return _route_service_time_at_position(
        route,
        position,
        _warehouse_ready_times(state).get(int(route[0]), 0.0),
        data,
        config,
    )


def _drone_customer_container_ready_time(
    customer: int,
    state: TVDState,
) -> Optional[float]:
    assignment = state.order_assignment.get(int(customer))
    if not isinstance(assignment, dict):
        return None
    container_id = int(assignment.get("container_id", -1))
    container_route = state.container_routes.get(container_id)
    if not isinstance(container_route, dict):
        return None
    return float(container_route.get("unload_complete", 0.0))


def _drone_flight_end_time(
    launch_time: float,
    launch: int,
    customers: List[int],
    recovery: int,
    data: InstanceData,
    config: TVDConfig,
) -> Tuple[float, List[Tuple[int, float]]]:
    drone_time = float(launch_time)
    service_starts: List[Tuple[int, float]] = []
    previous = int(launch)
    for customer in customers:
        customer = int(customer)
        drone_time += _travel_minutes(
            data.drone_distance_matrix[previous, customer],
            config.fleet.drone_speed_kmph,
        )
        earliest, _ = data.time_windows.get(customer, (0.0, float("inf")))
        service_start = max(drone_time, float(earliest))
        service_starts.append((customer, float(service_start)))
        drone_time = service_start + float(data.service_times.get(customer, 0.0))
        previous = customer
    drone_time += _travel_minutes(
        data.drone_distance_matrix[previous, int(recovery)],
        config.fleet.drone_speed_kmph,
    )
    return float(drone_time), service_starts


def _drone_local_sortie_record(
    sortie: dict,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    *,
    candidate: bool,
    index: int,
) -> Optional[Dict[str, object]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    launch, customers, recovery = sortie_nodes(sortie)
    launch_van = str(sortie.get("launch_van_id", ""))
    recovery_van = str(sortie.get("recovery_van_id", launch_van))
    launch_route = routes.get(launch_van)
    recovery_route = routes.get(recovery_van)
    if launch_route is None or recovery_route is None:
        return None

    launch_pos = int(sortie.get("launch_position", -1))
    recovery_pos = int(sortie.get("recovery_position", -1))
    launch_matches = 0 <= launch_pos < len(launch_route) and int(launch_route[launch_pos]) == launch
    recovery_matches = 0 <= recovery_pos < len(recovery_route) and int(recovery_route[recovery_pos]) == recovery
    if candidate and (not launch_matches or not recovery_matches):
        return None
    if not launch_matches:
        launch_pos = next((idx for idx, node in enumerate(launch_route) if int(node) == launch), -1)
    if not recovery_matches:
        recovery_pos = next((idx for idx, node in enumerate(recovery_route) if int(node) == recovery), -1)
    if launch_pos < 0 or recovery_pos < 0 or launch_pos == len(launch_route) - 1:
        return None

    launch_time = _route_position_time_from_state(
        state, launch_van, launch_route, launch_pos, "departure_time", data, config
    )
    recovery_arrival = _route_position_time_from_state(
        state, recovery_van, recovery_route, recovery_pos, "arrival_time", data, config
    )
    if launch_time is None or recovery_arrival is None:
        return None
    flight_end, _ = _drone_flight_end_time(
        float(launch_time), launch, customers, recovery, data, config
    )
    if not candidate:
        launch_time = max(float(launch_time), float(sortie.get("launch_time", 0.0)))
        flight_end, _ = _drone_flight_end_time(
            float(launch_time), launch, customers, recovery, data, config
        )
    recovery_time = max(
        float(recovery_arrival),
        float(flight_end),
        float(sortie.get("recovery_time", 0.0)) if not candidate else 0.0,
    )
    return {
        "candidate": candidate,
        "index": int(index),
        "sortie": sortie,
        "drone_id": str(sortie.get("drone_id", "")),
        "launch_van": launch_van,
        "recovery_van": recovery_van,
        "launch": int(launch),
        "recovery": int(recovery),
        "launch_pos": int(launch_pos),
        "recovery_pos": int(recovery_pos),
        "base_launch_time": float(launch_time),
        "recovery_arrival": float(recovery_arrival),
        "flight_end": float(flight_end),
        "recovery_time": float(recovery_time),
    }


def _drone_physical_local_check(
    customers: List[int],
    sortie: dict,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> Tuple[bool, Optional[str], Optional[Dict[str, object]]]:
    drone_id = str(sortie.get("drone_id", ""))
    if drone_id not in state.drone_initial_carrier:
        return False, "rejected_by_drone_carrier", None

    records: List[Dict[str, object]] = []
    for index, existing in enumerate(state.drone_sorties):
        if not isinstance(existing, dict):
            continue
        record = _drone_local_sortie_record(
            existing, state, data, config, candidate=False, index=index
        )
        if record is not None:
            records.append(record)
    candidate_record = _drone_local_sortie_record(
        sortie,
        state,
        data,
        config,
        candidate=True,
        index=len(state.drone_sorties),
    )
    if candidate_record is None:
        return False, "rejected_by_sync", None
    records.append(candidate_record)

    by_drone: Dict[str, List[Dict[str, object]]] = {}
    for record in records:
        by_drone.setdefault(str(record["drone_id"]), []).append(record)

    candidate_launch_time = float(candidate_record["base_launch_time"])
    candidate_recovery_time = float(candidate_record["recovery_time"])
    for current_drone_id, drone_records in by_drone.items():
        drone_records.sort(
            key=lambda record: (
                float(record["base_launch_time"]),
                int(record["launch_pos"]),
                int(record["index"]),
            )
        )
        current_carrier = str(state.drone_initial_carrier.get(current_drone_id, "unknown"))
        available_time = _warehouse_ready_times(state).get(
            int(state.van_home.get(current_carrier, state.selected_transshipment)),
            0.0,
        )
        previous_record: Optional[Dict[str, object]] = None
        candidate_seen = False
        for record in drone_records:
            is_candidate = bool(record["candidate"])
            launch_van = str(record["launch_van"])
            if (is_candidate or candidate_seen) and current_carrier != launch_van:
                return False, "rejected_by_drone_carrier", None
            if is_candidate and previous_record is not None:
                if (
                    str(previous_record["recovery_van"])
                    == str(record["launch_van"])
                    and int(record["launch_pos"]) < int(previous_record["recovery_pos"])
                ):
                    return False, "rejected_by_sortie_order", None
                if int(previous_record["recovery"]) in state.transshipment_nodes:
                    return False, "rejected_by_sortie_order", None

            effective_launch = max(float(record["base_launch_time"]), float(available_time))
            flight_end, _ = _drone_flight_end_time(
                effective_launch,
                int(record["launch"]),
                sortie_nodes(record["sortie"])[1],
                int(record["recovery"]),
                data,
                config,
            )
            recovery_time = max(float(record["recovery_arrival"]), float(flight_end))
            if not is_candidate:
                recovery_time = max(
                    recovery_time,
                    float(record["sortie"].get("recovery_time", 0.0)),
                )
            if is_candidate:
                candidate_seen = True
                candidate_launch_time = float(effective_launch)
                candidate_recovery_time = float(recovery_time)
                record["launch_time"] = candidate_launch_time
                record["recovery_time"] = candidate_recovery_time

            current_carrier = (
                "__warehouse__"
                if int(record["recovery"]) in state.transshipment_nodes
                else str(record["recovery_van"])
            )
            available_time = float(recovery_time)
            previous_record = record

    def capacity_peak(include_candidate: bool) -> int:
        counts: Dict[str, int] = {}
        for carrier in state.drone_initial_carrier.values():
            carrier = str(carrier)
            counts[carrier] = counts.get(carrier, 0) + 1
        events = []
        for record in records:
            if bool(record["candidate"]) and not include_candidate:
                continue
            events.append(
                (
                    float(record.get("launch_time", record["base_launch_time"])),
                    0,
                    str(record["launch_van"]),
                    -1,
                )
            )
            if int(record["recovery"]) not in state.transshipment_nodes:
                events.append(
                    (
                        float(record.get("recovery_time", record["recovery_time"])),
                        1,
                        str(record["recovery_van"]),
                        1,
                    )
                )
        peak = max(counts.values(), default=0)
        for event_time, event_kind, van_id, delta in sorted(events):
            del event_time, event_kind
            counts[van_id] = counts.get(van_id, 0) + delta
            peak = max(peak, counts[van_id])
        return peak

    max_carried = int(getattr(config.fleet, "max_drones_carried_per_van", 3))
    if capacity_peak(include_candidate=True) > max_carried and capacity_peak(include_candidate=False) <= max_carried:
        return False, "rejected_by_dynamic_drone_capacity", None

    candidate_record["launch_time"] = candidate_launch_time
    candidate_record["recovery_time"] = candidate_recovery_time
    return True, None, candidate_record


def _drone_downstream_route_feasible(
    recovery_van: str,
    recovery_pos: int,
    recovery_time: float,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    route = routes.get(str(recovery_van))
    if route is None or recovery_pos < 0 or recovery_pos >= len(route):
        return False
    position_time = _route_position_time_from_state(
        state,
        str(recovery_van),
        route,
        recovery_pos,
        "departure_time",
        data,
        config,
    )
    if position_time is None:
        return False
    current_time = max(float(position_time), float(recovery_time))
    previous = int(route[recovery_pos])
    for node in route[recovery_pos + 1 :]:
        node = int(node)
        current_time += _travel_minutes(
            data.ground_distance_matrix[previous, node],
            config.fleet.van_speed_kmph,
        )
        if node in data.customers and state.service_mode.get(node) == "van":
            earliest, latest = data.time_windows.get(node, (0.0, float("inf")))
            service_start = max(current_time, float(earliest))
            if service_start > float(latest) + 1e-9:
                return False
            current_time = service_start + float(data.service_times.get(node, 0.0))
        previous = node
    return True


def _drone_insert_hard_feasible_uncached(
    customers: List[int],
    sortie: dict,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> Tuple[bool, Optional[str]]:
    if not customers:
        return False, "drone_empty_sortie"
    if len(set(int(customer) for customer in customers)) != len(customers):
        return False, "drone_duplicate_customer"
    if any(not data.drone_eligible.get(int(customer), False) for customer in customers):
        return False, "drone_ineligible"
    served_by_van = set(state.get_van_customers())
    served_by_drone = set(state.get_drone_customers())
    if any(
        int(customer) not in state.unassigned
        or int(customer) in served_by_van
        or int(customer) in served_by_drone
        for customer in customers
    ):
        return False, "drone_customer_already_served"
    if drone_sortie_peak_payload(sortie, data, config) > config.fleet.drone_capacity_kg:
        return False, "rejected_by_drone_payload"
    if drone_sortie_distance(sortie, data) > config.fleet.drone_endurance_km:
        return False, "rejected_by_drone_endurance"
    if drone_sortie_energy(sortie, data, config) > config.fleet.drone_battery_capacity_kwh:
        return False, "rejected_by_drone_energy"
    if not _can_make_drone_sortie(sortie, data, config):
        return False, "drone_basic_feasibility"
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    launch_van_id = str(sortie.get("launch_van_id", ""))
    recovery_van_id = str(sortie.get("recovery_van_id", launch_van_id))
    launch_route = routes.get(launch_van_id)
    recovery_route = routes.get(recovery_van_id)
    if launch_route is None or recovery_route is None:
        return False, "rejected_by_sync"
    launch = int(sortie.get("launch", -1))
    recovery = int(sortie.get("recovery", -1))
    launch_pos = int(sortie.get("launch_position", -1))
    recovery_pos = int(sortie.get("recovery_position", -1))
    if not (0 <= launch_pos < len(launch_route) and int(launch_route[launch_pos]) == launch):
        return False, "rejected_by_sync"
    if not (0 <= recovery_pos < len(recovery_route) and int(recovery_route[recovery_pos]) == recovery):
        return False, "rejected_by_sync"
    if launch_pos == len(launch_route) - 1:
        return False, "rejected_by_sync"
    if launch_van_id == recovery_van_id:
        if recovery_pos < launch_pos:
            return False, "rejected_by_sync"
        if launch == recovery and recovery_pos != launch_pos:
            return False, "rejected_by_sync"

    ready = _warehouse_ready_times(state)
    launch_time = _route_service_time_at_position(
        launch_route,
        launch_pos,
        ready.get(int(launch_route[0]), 0.0),
        data,
        config,
    )
    recovery_arrival = _route_service_time_at_position(
        recovery_route,
        recovery_pos,
        ready.get(int(recovery_route[0]), 0.0),
        data,
        config,
    )
    if launch_time is None or recovery_arrival is None:
        return False, "rejected_by_sync"

    for customer in customers:
        assignment = state.order_assignment.get(int(customer))
        container_route = (
            state.container_routes.get(int(assignment.get("container_id", -1)))
            if isinstance(assignment, dict)
            else None
        )
        if not isinstance(container_route, dict):
            return False, "rejected_by_container_assignment"
        expected_warehouse = int(
            container_route.get("destination_warehouse", state.selected_transshipment)
        )
        if int(launch_route[0]) != expected_warehouse:
            return False, "rejected_by_container_warehouse"

    physical_ok, physical_reason, candidate_record = _drone_physical_local_check(
        customers, sortie, state, data, config
    )
    if not physical_ok or candidate_record is None:
        return False, physical_reason or "rejected_by_drone_carrier"

    effective_launch_time = float(candidate_record["launch_time"])
    drone_time, service_starts = _drone_flight_end_time(
        effective_launch_time, launch, [int(customer) for customer in customers], recovery, data, config
    )
    for customer, service_start in service_starts:
        _, latest = data.time_windows.get(int(customer), (0.0, float("inf")))
        if service_start > float(latest) + 1e-9:
            return False, "rejected_by_time_window"
        ready_time = _drone_customer_container_ready_time(int(customer), state)
        if ready_time is None or service_start + 1e-9 < ready_time:
            return False, "rejected_by_container_ready"

    if not _drone_downstream_route_feasible(
        str(sortie.get("recovery_van_id", sortie.get("launch_van_id", ""))),
        int(sortie.get("recovery_position", -1)),
        float(candidate_record["recovery_time"]),
        state,
        data,
        config,
    ):
        return False, "rejected_by_downstream_time_window"

    return bool(drone_time >= 0.0 and float(recovery_arrival) >= 0.0), None


def _drone_insert_hard_feasible(
    customers: List[int],
    sortie: dict,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    cache_key: Optional[Tuple[object, ...]] = None,
) -> bool:
    enabled = bool(getattr(config.alns, "enable_local_feasibility_cache", False))
    collect_stats = bool(
        getattr(config.alns, "collect_local_feasibility_cache_stats", False)
    )
    in_alns_loop = bool(getattr(config.alns, "_inside_alns_loop", False))
    if not in_alns_loop or not (enabled or collect_stats):
        feasible, reason = _drone_insert_hard_feasible_uncached(
            customers, sortie, state, data, config
        )
        if reason is not None:
            record_repair_rejection(reason)
        return feasible

    key = (
        cache_key
        if cache_key is not None
        else _drone_local_feasibility_cache_key(customers, sortie, state)
    )
    cached = get_local_feasibility_cache(key, enabled=enabled)
    if cached is not None:
        feasible, reason = cached
        if reason is not None:
            record_repair_rejection(reason)
        return bool(feasible)

    start = time.perf_counter()
    feasible, reason = _drone_insert_hard_feasible_uncached(
        customers, sortie, state, data, config
    )
    add_local_feasibility_eval_time(time.perf_counter() - start)
    set_local_feasibility_cache(key, (feasible, reason), enabled=enabled)
    if reason is not None:
        record_repair_rejection(reason)
    return feasible


def _best_van_move(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> Optional[InsertionMove]:
    if data.is_high_floor.get(int(customer), False):
        return None
    best: Optional[InsertionMove] = None
    routes = _repair_van_routes(state)
    for van_id, route in routes.items():
        if not _can_van_insert(customer, route, data, config):
            continue
        fixed_delta = 0.0 if len(route) > 2 else config.cost.van_fixed_cost
        for idx in range(1, len(route)):
            increment("van_insert_candidates")
            increment("service_mode_switch_candidates")
            if len(route) <= 2:
                increment("new_van_activation_candidates")
            candidate_route = route[:idx] + [int(customer)] + route[idx:]
            feasible = _van_insert_hard_feasible(
                customer,
                van_id,
                candidate_route,
                state,
                data,
                config,
            )
            record_repair_candidate("van", feasible)
            if not feasible:
                continue
            delta = _van_insert_cost(customer, route, idx, data)
            cost = delta * config.cost.van_cost_per_km + fixed_delta
            if best is None or cost < best.cost:
                best = InsertionMove(mode="van", cost=cost, index=idx, van_id=van_id)
    return best


def _enumerate_feasible_van_moves(
    customer: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[InsertionMove]:
    """Return every concrete hard-feasible van insertion for Regret-2."""
    if data.is_high_floor.get(int(customer), False):
        return []
    moves: List[InsertionMove] = []
    for van_id, route in _repair_van_routes(state).items():
        if not _can_van_insert(customer, route, data, config):
            continue
        fixed_delta = 0.0 if len(route) > 2 else config.cost.van_fixed_cost
        for idx in range(1, len(route)):
            increment("van_insert_candidates")
            increment("service_mode_switch_candidates")
            if len(route) <= 2:
                increment("new_van_activation_candidates")
            candidate_route = route[:idx] + [int(customer)] + route[idx:]
            feasible = _van_insert_hard_feasible(
                customer,
                van_id,
                candidate_route,
                state,
                data,
                config,
            )
            record_repair_candidate("van", feasible)
            if not feasible:
                continue
            delta = _van_insert_cost(customer, route, idx, data)
            moves.append(
                InsertionMove(
                    mode="van",
                    cost=delta * config.cost.van_cost_per_km + fixed_delta,
                    index=idx,
                    van_id=van_id,
                )
            )
    return moves


def _stable_van_id_key(van_id: str) -> Tuple[int, object]:
    """Return the existing numeric van order, with a stable string fallback."""
    text = str(van_id)
    try:
        return (0, int(text.rsplit("_", 1)[1]))
    except (IndexError, ValueError):
        return (1, text)


def _local_target_van(
    customer: int,
    state: TVDState,
) -> Tuple[Optional[str], str]:
    """Choose one Local target route without evaluating insertion costs.

    The paper semantics require one preselected route but do not specify how
    this toy state should recover it when destroy metadata is absent.  Use
    existing route ownership first, then the order/container warehouse, and
    finally the first existing route in stable van order.
    """
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    if not routes:
        return None, "no_existing_route"

    ordered_van_ids = sorted((str(van_id) for van_id in routes), key=_stable_van_id_key)

    def existing_van_id(value: object) -> Optional[str]:
        if isinstance(value, dict):
            for field in (
                "previous_van_id",
                "originating_van_id",
                "van_id",
                "route_id",
            ):
                if field in value:
                    candidate = existing_van_id(value[field])
                    if candidate is not None:
                        return candidate
            return None
        candidate = str(value)
        if candidate in routes:
            return candidate
        if candidate.isdigit() and f"van_{candidate}" in routes:
            return f"van_{candidate}"
        return None

    # Priority 1: route ownership retained by an upstream destroy/operator.
    for metadata_key in (
        "previous_van_assignment",
        "previous_route_ownership",
        "previous_service_route",
        "bundle_anchor_route",
        "originating_route",
    ):
        mapping = state.metadata.get(metadata_key)
        if not isinstance(mapping, dict):
            continue
        value = mapping.get(int(customer), mapping.get(str(int(customer))))
        target = existing_van_id(value) if value is not None else None
        if target is not None:
            return target, f"metadata:{metadata_key}"

    assignment = state.order_assignment.get(int(customer), {})
    if isinstance(assignment, dict):
        target = existing_van_id(assignment)
        if target is not None:
            return target, "order_assignment:route"

    # Priority 2: explicit order -> container -> destination warehouse mapping.
    warehouse: Optional[int] = None
    if isinstance(assignment, dict):
        container_id = assignment.get("container_id")
        if container_id is not None:
            container_route = state.container_routes.get(int(container_id), {})
            if isinstance(container_route, dict):
                destination = container_route.get("destination_warehouse")
                if destination is not None:
                    warehouse = int(destination)
        if warehouse is None and assignment.get("assigned_transshipment") is not None:
            warehouse = int(assignment["assigned_transshipment"])

    if warehouse is not None:
        warehouse_routes = [
            van_id
            for van_id in ordered_van_ids
            if int(state.van_home.get(van_id, routes[van_id][0] if routes[van_id] else -1))
            == warehouse
        ]
        if warehouse_routes:
            return warehouse_routes[0], "container_destination_warehouse"

    # Priority 3: minimal engineering fallback. This is deliberately not a
    # route-quality ranking and performs no candidate/cost evaluation.
    return ordered_van_ids[0], "stable_first_existing_route"


def _best_van_move_on_route(
    customer: int,
    target_van_id: str,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    trace: Optional[Dict[str, object]] = None,
) -> Optional[InsertionMove]:
    """Enumerate van insertion positions on exactly one existing route."""
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    route = routes.get(str(target_van_id))
    if route is None or data.is_high_floor.get(int(customer), False):
        return None
    if trace is not None:
        cast_ids = trace.setdefault("visited_van_ids", set())
        assert isinstance(cast_ids, set)
        cast_ids.add(str(target_van_id))
    if not _can_van_insert(customer, route, data, config):
        return None

    best: Optional[InsertionMove] = None
    fixed_delta = 0.0 if len(route) > 2 else config.cost.van_fixed_cost
    for idx in range(1, len(route)):
        increment("van_insert_candidates")
        increment("service_mode_switch_candidates")
        if len(route) <= 2:
            increment("new_van_activation_candidates")
        if trace is not None:
            trace["van_candidate_count"] = int(trace.get("van_candidate_count", 0)) + 1
        candidate_route = route[:idx] + [int(customer)] + route[idx:]
        feasible = _van_insert_hard_feasible(
            customer,
            str(target_van_id),
            candidate_route,
            state,
            data,
            config,
        )
        record_repair_candidate("van", feasible)
        if not feasible:
            continue
        delta = _van_insert_cost(customer, route, idx, data)
        cost = delta * config.cost.van_cost_per_km + fixed_delta
        if best is None or cost < best.cost:
            best = InsertionMove(
                mode="van",
                cost=cost,
                index=idx,
                van_id=str(target_van_id),
            )
    return best


def _drone_payload(customers: List[int], data: InstanceData) -> float:
    delivery = sum(data.demands[customer] for customer in customers)
    pickup = sum(getattr(data, "pickup_demands", {}).get(customer, 0.0) for customer in customers)
    return float(delivery + pickup)


def _can_make_drone_sortie(sortie: dict, data: InstanceData, config: TVDConfig) -> bool:
    _, customers, _ = sortie_nodes(sortie)
    if not customers:
        return False
    if any(not data.drone_eligible.get(customer, False) for customer in customers):
        return False
    if drone_sortie_peak_payload(sortie, data, config) > config.fleet.drone_capacity_kg:
        return False
    return (
        drone_sortie_distance(sortie, data) <= config.fleet.drone_endurance_km
        and drone_sortie_energy(sortie, data, config)
        <= config.fleet.drone_battery_capacity_kwh
    )


def _first_drone_for_van(state: TVDState, van_id: str) -> str:
    return next(
        (
            candidate_drone
            for candidate_drone, carrier in state.drone_initial_carrier.items()
            if carrier == van_id
        ),
        "",
    )


def _candidate_drones_for_launch_van(state: TVDState, van_id: str) -> List[str]:
    """Return every named drone that can possibly reach this launch van.

    This is only a safe necessary-condition filter.  Exact current-carrier,
    availability-time, existing-sortie order, and warehouse-return semantics
    remain owned by ``_drone_physical_local_check`` for each concrete sortie.
    """

    possible = {
        str(drone_id)
        for drone_id, carrier in state.drone_initial_carrier.items()
        if str(carrier) == str(van_id)
    }
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        drone_id = str(sortie.get("drone_id", ""))
        if drone_id not in state.drone_initial_carrier:
            continue
        _, _, recovery = sortie_nodes(sortie)
        recovery_van = str(
            sortie.get("recovery_van_id", sortie.get("launch_van_id", ""))
        )
        if recovery_van == str(van_id) and int(recovery) not in state.transshipment_nodes:
            possible.add(drone_id)
    return [
        str(drone_id)
        for drone_id in state.drone_initial_carrier
        if str(drone_id) in possible
    ]


def _extend_drone_customers(
    seed_customer: int,
    launch: int,
    recovery: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[int]:
    customers = [int(seed_customer)]
    while True:
        best_candidate = None
        best_distance = None
        for candidate in state.unassigned:
            candidate = int(candidate)
            if candidate in customers:
                continue
            if not data.drone_eligible.get(candidate, False):
                continue
            if any(candidate in route for route in state.van_routes.values()):
                continue
            trial_customers = customers + [candidate]
            trial_sortie = _make_drone_sortie(launch, trial_customers, recovery)
            if not _can_make_drone_sortie(trial_sortie, data, config):
                continue
            distance = drone_sortie_distance(trial_sortie, data)
            if best_distance is None or distance < best_distance:
                best_candidate = candidate
                best_distance = distance

        if best_candidate is None:
            break
        customers.append(best_candidate)
    return customers


def _best_drone_move_for_customers(
    customers: List[int],
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    allowed_launch_van_ids: Optional[Iterable[str]] = None,
    candidate_trace: Optional[Dict[str, object]] = None,
) -> Optional[InsertionMove]:
    if not config.fleet.drone_enabled or not customers:
        return None
    if any(not data.drone_eligible.get(customer, False) for customer in customers):
        return None
    if _drone_payload(customers, data) > config.fleet.drone_capacity_kg:
        return None

    best: Optional[InsertionMove] = None
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    existing_drone_ids = {
        str(existing.get("drone_id"))
        for existing in state.drone_sorties
        if isinstance(existing, dict)
    }
    existing_van_ids = {
        van_id
        for van_id, route in routes.items()
        if len(route) > 2
        or any(
            isinstance(sortie, dict)
            and (
                sortie.get("launch_van_id") == van_id
                or sortie.get("recovery_van_id") == van_id
            )
            for sortie in state.drone_sorties
        )
    }

    launch_scope = (
        None
        if allowed_launch_van_ids is None
        else {str(van_id) for van_id in allowed_launch_van_ids}
    )
    for launch_van_id, launch_route in routes.items():
        if launch_scope is not None and str(launch_van_id) not in launch_scope:
            continue
        candidate_drone_ids = _candidate_drones_for_launch_van(state, launch_van_id)
        if not candidate_drone_ids:
            continue
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            if int(launch) in customers:
                continue
            for drone_id in candidate_drone_ids:
                for recovery_van_id, recovery_route in routes.items():
                    for recovery_pos, recovery in enumerate(recovery_route):
                        if int(recovery) in customers:
                            continue
                        if launch_van_id == recovery_van_id:
                            if recovery_pos < launch_pos:
                                continue
                            if launch == recovery and recovery_pos != launch_pos:
                                continue
                        sortie = _make_drone_sortie(
                            launch,
                            customers,
                            recovery,
                            drone_id=drone_id,
                            launch_van_id=launch_van_id,
                            recovery_van_id=recovery_van_id,
                        )
                        sortie["launch_position"] = int(launch_pos)
                        sortie["recovery_position"] = int(recovery_pos)
                        candidate_key = _drone_local_feasibility_cache_key(
                            customers,
                            sortie,
                            state,
                        )
                        increment("drone_insert_candidates")
                        increment("service_mode_switch_candidates")
                        if candidate_trace is not None:
                            candidate_trace["drone_candidate_count"] = int(
                                candidate_trace.get("drone_candidate_count", 0)
                            ) + 1
                            launch_ids = candidate_trace.setdefault("launch_van_ids", set())
                            recovery_ids = candidate_trace.setdefault("recovery_van_ids", set())
                            assert isinstance(launch_ids, set)
                            assert isinstance(recovery_ids, set)
                            launch_ids.add(str(launch_van_id))
                            recovery_ids.add(str(recovery_van_id))
                        if launch_van_id != recovery_van_id:
                            increment("cross_van_docking_candidates")
                        for van_id in {launch_van_id, recovery_van_id}:
                            if van_id not in existing_van_ids:
                                increment("new_van_activation_candidates")
                        if not record_local_drone_candidate(candidate_key):
                            continue
                        feasible = _drone_insert_hard_feasible(
                            customers,
                            sortie,
                            state,
                            data,
                            config,
                            cache_key=candidate_key,
                        )
                        record_repair_candidate("drone", feasible)
                        if not feasible:
                            continue
                        fixed_delta = (
                            0.0
                            if drone_id in existing_drone_ids
                            else config.cost.drone_fixed_cost
                        )
                        van_fixed_delta = sum(
                            config.cost.van_fixed_cost
                            for van_id in {launch_van_id, recovery_van_id}
                            if van_id not in existing_van_ids
                        )
                        cost = (
                            drone_sortie_distance(sortie, data) * config.cost.drone_cost_per_km
                            + fixed_delta
                            + van_fixed_delta
                        )
                        move = InsertionMove(mode="drone", cost=cost, sortie=sortie)
                        if best is None or cost < best.cost:
                            best = move
    return best


def _enumerate_feasible_drone_moves_for_customers(
    customers: List[int],
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[InsertionMove]:
    """Return all concrete hard-feasible drone moves for one customer tuple."""
    if not config.fleet.drone_enabled or not customers:
        return []
    if any(not data.drone_eligible.get(customer, False) for customer in customers):
        return []
    if _drone_payload(customers, data) > config.fleet.drone_capacity_kg:
        return []

    moves: List[InsertionMove] = []
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    existing_drone_ids = {
        str(existing.get("drone_id"))
        for existing in state.drone_sorties
        if isinstance(existing, dict)
    }
    existing_van_ids = {
        van_id
        for van_id, route in routes.items()
        if len(route) > 2
        or any(
            isinstance(sortie, dict)
            and (
                sortie.get("launch_van_id") == van_id
                or sortie.get("recovery_van_id") == van_id
            )
            for sortie in state.drone_sorties
        )
    }

    for launch_van_id, launch_route in routes.items():
        candidate_drone_ids = _candidate_drones_for_launch_van(state, launch_van_id)
        if not candidate_drone_ids:
            continue
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            if int(launch) in customers:
                continue
            for drone_id in candidate_drone_ids:
                for recovery_van_id, recovery_route in routes.items():
                    for recovery_pos, recovery in enumerate(recovery_route):
                        if int(recovery) in customers:
                            continue
                        if launch_van_id == recovery_van_id:
                            if recovery_pos < launch_pos:
                                continue
                            if launch == recovery and recovery_pos != launch_pos:
                                continue
                        sortie = _make_drone_sortie(
                            launch,
                            customers,
                            recovery,
                            drone_id=drone_id,
                            launch_van_id=launch_van_id,
                            recovery_van_id=recovery_van_id,
                        )
                        sortie["launch_position"] = int(launch_pos)
                        sortie["recovery_position"] = int(recovery_pos)
                        candidate_key = _drone_local_feasibility_cache_key(
                            customers,
                            sortie,
                            state,
                        )
                        increment("drone_insert_candidates")
                        increment("service_mode_switch_candidates")
                        if launch_van_id != recovery_van_id:
                            increment("cross_van_docking_candidates")
                        for van_id in {launch_van_id, recovery_van_id}:
                            if van_id not in existing_van_ids:
                                increment("new_van_activation_candidates")
                        if not record_local_drone_candidate(candidate_key):
                            continue
                        feasible = _drone_insert_hard_feasible(
                            customers,
                            sortie,
                            state,
                            data,
                            config,
                            cache_key=candidate_key,
                        )
                        record_repair_candidate("drone", feasible)
                        if not feasible:
                            continue
                        fixed_delta = (
                            0.0
                            if drone_id in existing_drone_ids
                            else config.cost.drone_fixed_cost
                        )
                        van_fixed_delta = sum(
                            config.cost.van_fixed_cost
                            for van_id in {launch_van_id, recovery_van_id}
                            if van_id not in existing_van_ids
                        )
                        moves.append(
                            InsertionMove(
                                mode="drone",
                                cost=(
                                    drone_sortie_distance(sortie, data)
                                    * config.cost.drone_cost_per_km
                                    + fixed_delta
                                    + van_fixed_delta
                                ),
                                sortie=sortie,
                            )
                        )
    return moves


def _enumerate_feasible_drone_moves(
    customer: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[InsertionMove]:
    """Enumerate all unique customer tuples, then all concrete drone moves."""
    if not config.fleet.drone_enabled or not data.drone_eligible.get(customer, False):
        return []
    if (
        data.demands[customer]
        + getattr(data, "pickup_demands", {}).get(customer, 0.0)
        > config.fleet.drone_capacity_kg
    ):
        return []

    customer_tuples: List[Tuple[int, ...]] = [(int(customer),)]
    seen_customer_tuples = {customer_tuples[0]}
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    for launch_route in routes.values():
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            for recovery_route in routes.values():
                for recovery in recovery_route:
                    sortie_customers = tuple(
                        _extend_drone_customers(
                            customer,
                            launch,
                            recovery,
                            state,
                            data,
                            config,
                        )
                    )
                    if sortie_customers not in seen_customer_tuples:
                        seen_customer_tuples.add(sortie_customers)
                        customer_tuples.append(sortie_customers)

    moves: List[InsertionMove] = []
    for customer_tuple in customer_tuples:
        moves.extend(
            _enumerate_feasible_drone_moves_for_customers(
                list(customer_tuple),
                state,
                data,
                config,
            )
        )
    return moves


def _sortie_van_id(sortie: dict, field: str, fallback: str = "") -> str:
    value = sortie.get(field, fallback) if isinstance(sortie, dict) else fallback
    return str(value or fallback)


def _sortie_drone_id(sortie: dict) -> str:
    value = sortie.get("drone_id", "") if isinstance(sortie, dict) else ""
    return str(value or "")


def _copy_sortie_with_route(template: dict, launch: int, customers: List[int], recovery: int) -> dict:
    launch_pos = template.get("launch_position", 0)
    recovery_pos = template.get("recovery_position", launch_pos)
    return _make_drone_sortie(
        launch,
        customers,
        recovery,
        drone_id=_sortie_drone_id(template),
        launch_van_id=_sortie_van_id(template, "launch_van_id"),
        recovery_van_id=_sortie_van_id(
            template,
            "recovery_van_id",
            _sortie_van_id(template, "launch_van_id"),
        ),
    ) | {
        "launch_position": int(launch_pos),
        "recovery_position": int(recovery_pos),
    }


def _state_is_feasible_and_no_worse(
    base: TVDState,
    candidate: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> bool:
    feasible, _ = check_solution_feasible(candidate, data, config)
    if not feasible:
        return False
    base_cost, _ = objective(base.copy(), data, config)
    candidate_cost, _ = objective(candidate, data, config)
    return candidate_cost <= base_cost + 1e-9


def _replace_sorties_with_merged(
    state: TVDState,
    indices: List[int],
    merged_sortie: dict,
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    candidate = state.copy()
    remove_set = set(indices)
    candidate.drone_sorties = [
        sortie for idx, sortie in enumerate(candidate.drone_sorties) if idx not in remove_set
    ]
    candidate.drone_sorties.append(merged_sortie)
    for customer in sortie_nodes(merged_sortie)[1]:
        candidate.service_mode[int(customer)] = "drone"
    if _state_is_feasible_and_no_worse(state, candidate, data, config):
        return candidate
    return None


def _merge_sortie_group(
    state: TVDState,
    group: List[Tuple[int, dict]],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    ordered = sorted(
        group,
        key=lambda item: (
            float(item[1].get("launch_time", 0.0)),
            int(item[1].get("launch_position", 0)),
            int(item[0]),
        ),
    )
    for candidate_group in [ordered] + [
        list(pair) for pair in combinations(ordered, 2)
    ]:
        customers: List[int] = []
        for _, sortie in candidate_group:
            customers.extend(sortie_nodes(sortie)[1])
        if len(set(customers)) != len(customers):
            continue
        first_sortie = candidate_group[0][1]
        launch, _, recovery = sortie_nodes(first_sortie)
        merged_sortie = _copy_sortie_with_route(first_sortie, launch, customers, recovery)
        if not _can_make_drone_sortie(merged_sortie, data, config):
            continue
        merged = _replace_sorties_with_merged(
            state,
            [idx for idx, _ in candidate_group],
            merged_sortie,
            data,
            config,
        )
        if merged is not None:
            return merged
    return None


def _merge_adjacent_same_van_pair(
    state: TVDState,
    group: List[Tuple[int, dict]],
    data: InstanceData,
    config: TVDConfig,
) -> Optional[TVDState]:
    ordered = sorted(
        group,
        key=lambda item: (
            int(item[1].get("launch_position", 0)),
            int(item[1].get("recovery_position", 0)),
            float(item[1].get("launch_time", 0.0)),
        ),
    )
    for left, right in zip(ordered, ordered[1:]):
        left_idx, left_sortie = left
        right_idx, right_sortie = right
        launch, left_customers, _ = sortie_nodes(left_sortie)
        _, right_customers, recovery = sortie_nodes(right_sortie)
        customers = left_customers + right_customers
        if len(set(customers)) != len(customers):
            continue
        merged_sortie = _copy_sortie_with_route(left_sortie, launch, customers, recovery)
        merged_sortie["recovery_position"] = int(right_sortie.get("recovery_position", 0))
        merged_sortie["recovery"] = int(recovery)
        merged_sortie["recovery_van_id"] = _sortie_van_id(
            right_sortie,
            "recovery_van_id",
            _sortie_van_id(left_sortie, "recovery_van_id"),
        )
        if not _can_make_drone_sortie(merged_sortie, data, config):
            continue
        merged = _replace_sorties_with_merged(
            state,
            [left_idx, right_idx],
            merged_sortie,
            data,
            config,
        )
        if merged is not None:
            return merged
    return None


def consolidate_drone_sorties(
    state: TVDState, data: InstanceData, config: TVDConfig
) -> TVDState:
    """Merge compatible drone sorties when doing so is feasible and no worse."""

    feasible, _ = check_solution_feasible(state, data, config)
    if not feasible or len(state.drone_sorties) < 2:
        return state

    consolidated = state.copy()
    progress = True
    while progress:
        progress = False
        exact_groups: Dict[Tuple[object, ...], List[Tuple[int, dict]]] = {}
        same_van_groups: Dict[Tuple[object, ...], List[Tuple[int, dict]]] = {}
        for idx, sortie in enumerate(consolidated.drone_sorties):
            if not isinstance(sortie, dict):
                continue
            launch, _, recovery = sortie_nodes(sortie)
            launch_van = _sortie_van_id(sortie, "launch_van_id")
            recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
            exact_groups.setdefault(
                (launch_van, recovery_van, int(launch), int(recovery)),
                [],
            ).append((idx, sortie))
            same_van_groups.setdefault((launch_van, recovery_van), []).append(
                (idx, sortie)
            )

        for group in exact_groups.values():
            if len(group) < 2:
                continue
            merged = _merge_sortie_group(consolidated, group, data, config)
            if merged is not None:
                consolidated = merged
                progress = True
                break
        if progress:
            continue

        for group in same_van_groups.values():
            if len(group) < 2:
                continue
            merged = _merge_adjacent_same_van_pair(consolidated, group, data, config)
            if merged is not None:
                consolidated = merged
                progress = True
                break

    return consolidated


def _best_drone_move(
    customer: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    allowed_launch_van_ids: Optional[Iterable[str]] = None,
    candidate_trace: Optional[Dict[str, object]] = None,
) -> Optional[InsertionMove]:
    if not config.fleet.drone_enabled or not data.drone_eligible.get(customer, False):
        return None
    if data.demands[customer] + getattr(data, "pickup_demands", {}).get(customer, 0.0) > config.fleet.drone_capacity_kg:
        return None

    # The outer anchor loops can produce the same sortie customer sequence
    # more than once.  Memoize only within this call: state is not mutated by
    # the generator, and a later repair/state revision gets a fresh memo.
    move_by_customer_tuple: Dict[Tuple[int, ...], Optional[InsertionMove]] = {}

    def best_move_for_customer_tuple(sortie_customers: List[int]) -> Optional[InsertionMove]:
        customer_tuple = tuple(int(item) for item in sortie_customers)
        if customer_tuple not in move_by_customer_tuple:
            move_by_customer_tuple[customer_tuple] = _best_drone_move_for_customers(
                list(customer_tuple),
                state,
                data,
                config,
                allowed_launch_van_ids=allowed_launch_van_ids,
                candidate_trace=candidate_trace,
            )
        return move_by_customer_tuple[customer_tuple]

    best: Optional[InsertionMove] = None
    single_customer_move = best_move_for_customer_tuple([int(customer)])
    if single_customer_move is not None:
        best = single_customer_move

    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    launch_scope = (
        None
        if allowed_launch_van_ids is None
        else {str(van_id) for van_id in allowed_launch_van_ids}
    )
    for launch_van_id, launch_route in routes.items():
        if launch_scope is not None and str(launch_van_id) not in launch_scope:
            continue
        for launch_pos, launch in enumerate(launch_route):
            if launch_pos == len(launch_route) - 1:
                continue
            for recovery_route in routes.values():
                for recovery in recovery_route:
                    sortie_customers = _extend_drone_customers(
                        customer, launch, recovery, state, data, config
                    )
                    move = best_move_for_customer_tuple(sortie_customers)
                    if move is not None and (best is None or move.cost < best.cost):
                        best = move
    return best


def _make_drone_sortie(
    launch: int,
    customers,
    recovery: int,
    drone_id: str = "",
    launch_van_id: str = "",
    recovery_van_id: str = "",
) -> dict:
    if isinstance(customers, int):
        customers = [customers]
    return {
        "launch": int(launch),
        "customers": [int(customer) for customer in customers],
        "recovery": int(recovery),
        "launch_time": 0.0,
        "recovery_time": 0.0,
        "van_waiting_time": 0.0,
        "drone_waiting_time": 0.0,
        "same_node": bool(launch == recovery),
        "drone_id": drone_id,
        "launch_van_id": launch_van_id,
        "recovery_van_id": recovery_van_id,
    }


def _all_moves(customer: int, state: TVDState, data: InstanceData, config: TVDConfig) -> List[InsertionMove]:
    moves = []
    van = _best_van_move(customer, state, data, config)
    drone = _best_drone_move(customer, state, data, config)
    if van is not None and not data.is_high_floor.get(customer, False):
        moves.append(van)
    if drone is not None:
        moves.append(drone)
    return sorted(moves, key=lambda move: move.cost)


def _finalize_repair(state: TVDState, data: InstanceData, config: TVDConfig) -> TVDState:
    return consolidate_drone_sorties(state, data, config)


def _apply_move(state: TVDState, customer: int, move: InsertionMove) -> None:
    if move.mode == "van":
        assert move.index is not None
        assert move.van_id is not None
        state.van_routes.setdefault(
            move.van_id,
            [int(state.van_home.get(move.van_id, state.selected_transshipment)), int(state.selected_transshipment)],
        )
        state.van_routes[move.van_id].insert(move.index, customer)
        state.sync_primary_van_route()
        state.service_mode[customer] = "van"
    elif move.mode == "drone":
        assert move.sortie is not None
        state.drone_sorties.append(move.sortie)
        _, sortie_customers, _ = sortie_nodes(move.sortie)
        for drone_customer in sortie_customers:
            state.service_mode[drone_customer] = "drone"
            state.clean_unassigned(drone_customer)
    else:
        raise ValueError(f"unknown insertion mode: {move.mode}")
    state.clean_unassigned(customer)


@removal_context_boundary
def greedy_van_repair(
    state: TVDState,
    rng: np.random.Generator,
    data: InstanceData,
    config: TVDConfig,
    trace_collector: Optional[Callable[[Dict[str, object]], None]] = None,
) -> TVDState:
    caller = active_repair_name()
    enter_repair("greedy_van_repair")
    try:
        repaired = state.copy()
        rng.shuffle(repaired.unassigned)

        # Preserve the pre-Stage-2B greedy-drone fallback semantics. The
        # registered Local operator takes the route-scoped path below.
        if caller == "greedy_drone_repair":
            for customer in repaired.unassigned.copy():
                if customer not in repaired.unassigned:
                    continue
                if data.is_high_floor.get(customer, False):
                    continue
                move = _best_van_move(customer, repaired, data, config)
                if move is not None:
                    _apply_move(repaired, customer, move)
            return _finalize_repair(repaired, data, config)

        for customer in repaired.unassigned.copy():
            if customer not in repaired.unassigned:
                continue
            target_van_id, target_source = _local_target_van(customer, repaired)
            trace: Dict[str, object] = {
                "operator": "local_greedy",
                "customer_id": int(customer),
                "target_van_id": target_van_id,
                "target_route_source": target_source,
                "visited_van_ids": set(),
                "van_candidate_count": 0,
                "drone_candidate_count": 0,
                "launch_van_ids": set(),
                "recovery_van_ids": set(),
                "selected_mode": None,
                "selected_van_id": None,
                "selected_launch_van_id": None,
                "selected_recovery_van_id": None,
                "selected_cost": None,
            }
            if target_van_id is None:
                if trace_collector is not None:
                    trace_collector(trace)
                continue

            van_move = _best_van_move_on_route(
                customer,
                target_van_id,
                repaired,
                data,
                config,
                trace,
            )
            drone_move = _best_drone_move(
                customer,
                repaired,
                data,
                config,
                allowed_launch_van_ids={target_van_id},
                candidate_trace=trace,
            )
            moves = [move for move in (van_move, drone_move) if move is not None]
            moves.sort(key=lambda move: move.cost)
            if moves:
                selected = moves[0]
                trace["selected_mode"] = selected.mode
                trace["selected_cost"] = float(selected.cost)
                if selected.mode == "van":
                    trace["selected_van_id"] = selected.van_id
                elif selected.sortie is not None:
                    trace["selected_launch_van_id"] = selected.sortie.get(
                        "launch_van_id"
                    )
                    trace["selected_recovery_van_id"] = selected.sortie.get(
                        "recovery_van_id"
                    )
                _apply_move(repaired, customer, selected)

            if trace_collector is not None:
                for key in (
                    "visited_van_ids",
                    "launch_van_ids",
                    "recovery_van_ids",
                ):
                    value = trace.get(key)
                    if isinstance(value, set):
                        trace[key] = sorted(value, key=_stable_van_id_key)
                trace_collector(trace)
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("greedy_van_repair")


@removal_context_boundary
def greedy_drone_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("greedy_drone_repair")
    try:
        repaired = state.copy()
        for customer in repaired.unassigned.copy():
            if customer not in repaired.unassigned:
                continue
            move = _best_drone_move(customer, repaired, data, config)
            if move is not None:
                _apply_move(repaired, customer, move)
        if repaired.unassigned:
            repaired = greedy_van_repair(repaired, rng, data, config)
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("greedy_drone_repair")


@removal_context_boundary
def best_mode_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("best_mode_repair")
    try:
        repaired = state.copy()
        for customer in repaired.unassigned.copy():
            if customer not in repaired.unassigned:
                continue
            moves = _all_moves(customer, repaired, data, config)
            if moves:
                _apply_move(repaired, customer, moves[0])
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("best_mode_repair")


def _regret_move_identity(
    customer: int,
    move: InsertionMove,
    state: TVDState,
) -> Tuple[object, ...]:
    """Stable complete identity used for Regret-only deduplication."""
    assignment = state.order_assignment.get(int(customer), {})
    container_id = int(assignment.get("container_id", -1)) if isinstance(assignment, dict) else -1
    assigned_warehouse = (
        int(assignment.get("assigned_transshipment", -1))
        if isinstance(assignment, dict)
        else -1
    )
    if move.mode == "van":
        van_id = str(move.van_id or "")
        route = _repair_van_routes(state).get(van_id, [])
        return (
            "van",
            int(customer),
            van_id,
            tuple(int(node) for node in route),
            int(move.index if move.index is not None else -1),
            int(state.van_home.get(van_id, state.selected_transshipment)),
            container_id,
            assigned_warehouse,
        )

    sortie = move.sortie or {}
    launch, sortie_customers, recovery = sortie_nodes(sortie)
    launch_van = str(sortie.get("launch_van_id", ""))
    recovery_van = str(sortie.get("recovery_van_id", launch_van))
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    return (
        "drone",
        int(customer),
        str(sortie.get("drone_id", "")),
        launch_van,
        int(launch),
        int(sortie.get("launch_position", -1)),
        tuple(int(node) for node in routes.get(launch_van, [])),
        recovery_van,
        int(recovery),
        int(sortie.get("recovery_position", -1)),
        tuple(int(node) for node in routes.get(recovery_van, [])),
        tuple(int(item) for item in sortie_customers),
        container_id,
        assigned_warehouse,
    )


def _deduplicate_regret_moves(
    customer: int,
    moves: List[InsertionMove],
    state: TVDState,
) -> List[InsertionMove]:
    """Implementation choice: deduplicate by move identity, never by cost."""
    unique: Dict[Tuple[object, ...], InsertionMove] = {}
    for move in moves:
        identity = _regret_move_identity(customer, move, state)
        if identity not in unique:
            unique[identity] = move
    return list(unique.values())


def _copy_move(move: InsertionMove, *, cost: Optional[float] = None) -> InsertionMove:
    sortie = None
    if move.sortie is not None:
        sortie = dict(move.sortie)
        sortie["customers"] = list(move.sortie.get("customers", []))
    return InsertionMove(
        mode=move.mode,
        cost=float(move.cost if cost is None else cost),
        index=move.index,
        van_id=move.van_id,
        sortie=sortie,
    )


def _score_regret_moves_with_exact_objective_delta(
    customer: int,
    moves: List[InsertionMove],
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[InsertionMove]:
    """Score Regret candidates by exact full-objective delta on State copies."""
    base_cost, _ = objective(state.copy(), data, config)
    scored: List[InsertionMove] = []
    for move in moves:
        candidate = state.copy()
        candidate_move = _copy_move(move)
        _apply_move(candidate, customer, candidate_move)
        candidate_cost, _ = objective(candidate, data, config)
        scored.append(_copy_move(move, cost=float(candidate_cost - base_cost)))
    return scored


def _regret_move_order_key(
    customer: int,
    move: InsertionMove,
    state: TVDState,
) -> Tuple[object, ...]:
    # Preserve the existing stable van-before-drone tie behavior, then use
    # complete identity so equal-cost concrete strategies remain deterministic.
    mode_order = 0 if move.mode == "van" else 1
    return (float(move.cost), mode_order, _regret_move_identity(customer, move, state))


def _enumerate_regret_moves(
    customer: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> Tuple[List[InsertionMove], Dict[str, object]]:
    started = time.perf_counter()
    van_moves = _enumerate_feasible_van_moves(customer, state, data, config)
    drone_moves = _enumerate_feasible_drone_moves(customer, state, data, config)
    raw_moves = van_moves + drone_moves
    unique_moves = _deduplicate_regret_moves(customer, raw_moves, state)
    scored_moves = _score_regret_moves_with_exact_objective_delta(
        customer,
        unique_moves,
        state,
        data,
        config,
    )
    return scored_moves, {
        "raw_candidate_count": len(raw_moves),
        "unique_candidate_count": len(unique_moves),
        "van_candidate_count": len(van_moves),
        "drone_candidate_count": len(drone_moves),
        "enumeration_seconds": time.perf_counter() - started,
    }


def _evaluate_regret_customer(
    customer: int,
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    original_order: int,
) -> Tuple[Optional[RegretEvaluation], Dict[str, object]]:
    moves, stats = _enumerate_regret_moves(customer, state, data, config)
    ranking_started = time.perf_counter()
    moves.sort(key=lambda move: _regret_move_order_key(customer, move, state))
    ranking_seconds = time.perf_counter() - ranking_started
    stats["ranking_seconds"] = ranking_seconds
    if not moves:
        return None, stats
    second_move = moves[1] if len(moves) > 1 else None
    regret = (
        float(second_move.cost - moves[0].cost)
        if second_move is not None
        else None
    )
    return (
        RegretEvaluation(
            customer=int(customer),
            moves=moves,
            best_move=moves[0],
            second_move=second_move,
            regret=regret,
            original_order=int(original_order),
            raw_candidate_count=int(stats["raw_candidate_count"]),
            van_candidate_count=int(stats["van_candidate_count"]),
            drone_candidate_count=int(stats["drone_candidate_count"]),
            enumeration_seconds=float(stats["enumeration_seconds"]),
            ranking_seconds=float(ranking_seconds),
        ),
        stats,
    )


def _regret_customer_priority_key(
    evaluation: RegretEvaluation,
) -> Tuple[object, ...]:
    """Return an ascending key for the required customer priority.

    Implementation choice: the paper does not explicitly specify how to
    handle a customer with only one feasible insertion strategy. Such a
    customer receives structured priority above every multi-candidate one.
    """
    if evaluation.second_move is None:
        return (
            0,
            float(evaluation.best_move.cost),
            evaluation.original_order,
            evaluation.customer,
        )
    assert evaluation.regret is not None
    return (
        1,
        -float(evaluation.regret),
        float(evaluation.best_move.cost),
        evaluation.original_order,
        evaluation.customer,
    )


def _regret_trace_event(
    evaluation: Optional[RegretEvaluation],
    stats: Dict[str, object],
    *,
    customer: int,
    round_index: int,
    selected_customer: Optional[int],
    repair_elapsed_seconds: float,
) -> Dict[str, object]:
    best_move = evaluation.best_move if evaluation is not None else None
    second_move = evaluation.second_move if evaluation is not None else None
    return {
        "repair": "regret_repair",
        "round": int(round_index),
        "state_revision": int(round_index),
        "customer_id": int(customer),
        "raw_candidate_count": int(stats.get("raw_candidate_count", 0)),
        "unique_candidate_count": int(stats.get("unique_candidate_count", 0)),
        "van_candidate_count": int(stats.get("van_candidate_count", 0)),
        "drone_candidate_count": int(stats.get("drone_candidate_count", 0)),
        "best_move_identity": (
            _regret_move_identity(customer, best_move, stats["state"])
            if best_move is not None
            else None
        ),
        "best_delta": float(best_move.cost) if best_move is not None else None,
        "second_move_identity": (
            _regret_move_identity(customer, second_move, stats["state"])
            if second_move is not None
            else None
        ),
        "second_delta": float(second_move.cost) if second_move is not None else None,
        "regret": evaluation.regret if evaluation is not None else None,
        "single_candidate": bool(
            evaluation is not None and evaluation.second_move is None
        ),
        "customer_priority_key": (
            _regret_customer_priority_key(evaluation)
            if evaluation is not None
            else None
        ),
        "selected_customer": selected_customer,
        "selected": int(customer) == selected_customer,
        "enumeration_seconds": float(stats.get("enumeration_seconds", 0.0)),
        "ranking_seconds": float(stats.get("ranking_seconds", 0.0)),
        "repair_elapsed_seconds": float(repair_elapsed_seconds),
    }


@removal_context_boundary
def regret_repair(
    state: TVDState,
    rng: np.random.Generator,
    data: InstanceData,
    config: TVDConfig,
    trace_collector: Optional[Callable[[Dict[str, object]], None]] = None,
) -> TVDState:
    enter_repair("regret_repair")
    repair_started = time.perf_counter()
    try:
        repaired = state.copy()
        original_order = {
            int(customer): index
            for index, customer in enumerate(repaired.unassigned)
        }
        round_index = 0
        while repaired.unassigned:
            round_index += 1
            evaluations: List[RegretEvaluation] = []
            trace_rows = []
            for customer in repaired.unassigned:
                evaluation, stats = _evaluate_regret_customer(
                    customer,
                    repaired,
                    data,
                    config,
                    original_order.get(int(customer), len(original_order)),
                )
                stats["state"] = repaired
                trace_rows.append((int(customer), evaluation, stats))
                if evaluation is not None:
                    evaluations.append(evaluation)

            if not evaluations:
                if trace_collector is not None:
                    for customer, evaluation, stats in trace_rows:
                        trace_collector(
                            _regret_trace_event(
                                evaluation,
                                stats,
                                customer=customer,
                                round_index=round_index,
                                selected_customer=None,
                                repair_elapsed_seconds=time.perf_counter()
                                - repair_started,
                            )
                        )
                break

            selected = min(evaluations, key=_regret_customer_priority_key)
            if trace_collector is not None:
                for customer, evaluation, stats in trace_rows:
                    trace_collector(
                        _regret_trace_event(
                            evaluation,
                            stats,
                            customer=customer,
                            round_index=round_index,
                            selected_customer=selected.customer,
                            repair_elapsed_seconds=time.perf_counter()
                            - repair_started,
                        )
                    )
            _apply_move(repaired, selected.customer, selected.best_move)
        return _finalize_repair(repaired, data, config)
    finally:
        exit_repair("regret_repair")


def _finish_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    finished = state.copy()
    progress = True
    while finished.unassigned and progress:
        progress = False
        for customer in finished.unassigned.copy():
            moves = _all_moves(customer, finished, data, config)
            if moves:
                _apply_move(finished, customer, moves[0])
                progress = True
    return finished


def _cascade_state_copy(
    state: TVDState, metrics: Dict[str, object]
) -> TVDState:
    metrics["state_copy_count"] = int(metrics.get("state_copy_count", 0)) + 1
    return state.copy()


def _stable_freeze(value: object) -> object:
    if isinstance(value, dict):
        return tuple(
            (str(key), _stable_freeze(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_stable_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_stable_freeze(item) for item in value), key=repr))
    return value


def _sortie_structural_identity(sortie: object) -> Tuple[object, ...]:
    if not isinstance(sortie, dict):
        return ("legacy", _stable_freeze(sortie))
    launch, customers, recovery = sortie_nodes(sortie)
    return (
        str(sortie.get("drone_id", "")),
        str(sortie.get("launch_van_id", "")),
        int(launch),
        int(sortie.get("launch_position", -1)),
        tuple(int(customer) for customer in customers),
        str(sortie.get("recovery_van_id", sortie.get("launch_van_id", ""))),
        int(recovery),
        int(sortie.get("recovery_position", -1)),
    )


def _route_segment_contract_id(snapshot: VanRouteSegmentSnapshot) -> str:
    if snapshot.start_position < 0 or snapshot.end_position < 0:
        return f"van:{snapshot.van_id}:unresolved"
    return (
        f"van:{snapshot.van_id}:"
        f"{snapshot.start_position}-{snapshot.end_position}"
    )


def _validate_bundle_snapshot(
    bundle: CascadeBundleSnapshot,
    contract: Dict[str, object],
    state: TVDState,
) -> List[str]:
    errors: List[str] = []
    customers = tuple(int(customer) for customer in bundle.customer_ids)
    customer_set = set(customers)
    if bundle.schema_version != CASCADE_CONTRACT_SCHEMA_VERSION:
        errors.append(f"{bundle.bundle_id}: schema mismatch")
    if bundle.source_operator != CASCADE_SOURCE_OPERATOR:
        errors.append(f"{bundle.bundle_id}: source operator mismatch")
    if bundle.source_destroy_call_id != contract.get("destroy_call_id"):
        errors.append(f"{bundle.bundle_id}: destroy revision mismatch")
    if bundle.source_state_fingerprint != contract.get("source_state_fingerprint"):
        errors.append(f"{bundle.bundle_id}: source fingerprint mismatch")
    if not bundle.captured_before_removal:
        errors.append(f"{bundle.bundle_id}: snapshot was not captured before removal")
    if not customers or len(customer_set) != len(customers):
        errors.append(f"{bundle.bundle_id}: customer membership is empty or duplicated")
    if set(bundle.dependency_order) != customer_set or len(bundle.dependency_order) != len(
        customers
    ):
        errors.append(f"{bundle.bundle_id}: dependency_order is not the bundle membership")
    if bundle.dependency_order_semantics != (
        "current implementation order; Paper unspecified"
    ):
        errors.append(f"{bundle.bundle_id}: dependency_order semantics mismatch")

    services = bundle.customer_service_snapshots
    if (
        not all(isinstance(item, CustomerServiceSnapshot) for item in services)
        or {item.customer_id for item in services} != customer_set
        or len(services) != len(customers)
    ):
        errors.append(f"{bundle.bundle_id}: customer service snapshots mismatch")
    else:
        for service in services:
            if service.service_mode not in {"van", "drone"}:
                errors.append(
                    f"{bundle.bundle_id}: customer {service.customer_id} has invalid source mode"
                )
            if service.service_mode == "van" and len(service.van_route_positions) != 1:
                errors.append(
                    f"{bundle.bundle_id}: van customer {service.customer_id} lacks one route position"
                )

    route_snapshots = bundle.affected_route_segments
    drone_snapshots = bundle.removed_drone_subroutes
    link_snapshots = bundle.launch_recovery_snapshots
    carrier_snapshots = bundle.carrier_transfer_snapshots
    if not all(isinstance(item, VanRouteSegmentSnapshot) for item in route_snapshots):
        errors.append(f"{bundle.bundle_id}: invalid route snapshots")
    if not all(isinstance(item, DroneSubrouteSnapshot) for item in drone_snapshots):
        errors.append(f"{bundle.bundle_id}: invalid sortie snapshots")
    if not all(isinstance(item, LaunchRecoverySnapshot) for item in link_snapshots):
        errors.append(f"{bundle.bundle_id}: invalid launch/recovery snapshots")
    if not all(isinstance(item, CarrierTransferSnapshot) for item in carrier_snapshots):
        errors.append(f"{bundle.bundle_id}: invalid carrier snapshots")

    route_vans = {item.van_id for item in route_snapshots}
    for service in services:
        for position in service.van_route_positions:
            if position.van_id not in route_vans:
                errors.append(
                    f"{bundle.bundle_id}: van position is outside affected route scope"
                )
    if any(not set(item.customer_ids).issubset(customer_set) for item in drone_snapshots):
        errors.append(f"{bundle.bundle_id}: sortie includes a customer outside the bundle")
    drone_customer_ids = {
        customer
        for snapshot in drone_snapshots
        for customer in snapshot.customer_ids
    }
    expected_drone_customers = {
        service.customer_id
        for service in services
        if service.service_mode == "drone"
    }
    if drone_customer_ids != expected_drone_customers:
        errors.append(f"{bundle.bundle_id}: drone service/sortie membership mismatch")

    sortie_ids = tuple(item.sortie_id for item in drone_snapshots)
    if {item.sortie_id for item in link_snapshots} != set(sortie_ids):
        errors.append(f"{bundle.bundle_id}: launch/recovery links mismatch sorties")
    if {item.sortie_id for item in carrier_snapshots} != set(sortie_ids):
        errors.append(f"{bundle.bundle_id}: carrier links mismatch sorties")
    for link in link_snapshots:
        if link.launch_van_id not in route_vans or link.recovery_van_id not in route_vans:
            errors.append(f"{bundle.bundle_id}: launch/recovery van is outside route scope")

    scope = bundle.affected_structure_scope
    expected_route_ids = tuple(_route_segment_contract_id(item) for item in route_snapshots)
    expected_link_ids = tuple(
        edge
        for sortie_id in sortie_ids
        for edge in (f"{sortie_id}:launch", f"{sortie_id}:recovery")
    )
    expected_carrier_ids = tuple(f"{sortie_id}:carrier" for sortie_id in sortie_ids)
    expected_coordination_ids = tuple(
        edge
        for sortie_id in sortie_ids
        for edge in (
            f"{sortie_id}:truck-van-context",
            f"{sortie_id}:van-drone-launch",
            f"{sortie_id}:van-drone-recovery",
        )
    )
    if scope.van_route_segment_ids != expected_route_ids:
        errors.append(f"{bundle.bundle_id}: affected route scope mismatch")
    if scope.drone_subroute_ids != sortie_ids:
        errors.append(f"{bundle.bundle_id}: affected sortie scope mismatch")
    if scope.launch_recovery_link_ids != expected_link_ids:
        errors.append(f"{bundle.bundle_id}: affected launch/recovery scope mismatch")
    if scope.carrier_link_ids != expected_carrier_ids:
        errors.append(f"{bundle.bundle_id}: affected carrier scope mismatch")
    if scope.coordination_edge_ids != expected_coordination_ids:
        errors.append(f"{bundle.bundle_id}: affected coordination scope mismatch")
    expected_truck_context = f"selected_transshipment:{state.selected_transshipment}"
    if expected_truck_context not in scope.truck_context_ids:
        errors.append(f"{bundle.bundle_id}: truck/warehouse context mismatch")
    if bundle.truck_warehouse_context.selected_transshipment != state.selected_transshipment:
        errors.append(f"{bundle.bundle_id}: selected transshipment snapshot mismatch")
    return errors


def _validated_cascade_bundles(
    state: TVDState,
) -> Tuple[Optional[List[CascadeBundleSnapshot]], List[str]]:
    contract = state.metadata.get("cascade_contract")
    raw_bundles = state.metadata.get("cascade_bundles")
    if not isinstance(contract, dict) or not isinstance(raw_bundles, list):
        return None, ["missing cascade contract or bundle metadata"]
    if not cascade_metadata_is_current(state):
        return None, ["cascade contract is stale or does not match destroyed State"]
    if not all(isinstance(bundle, CascadeBundleSnapshot) for bundle in raw_bundles):
        return None, ["cascade bundle metadata contains an unsupported snapshot"]

    bundles = list(raw_bundles)
    errors: List[str] = []
    bundle_ids = [bundle.bundle_id for bundle in bundles]
    if len(set(bundle_ids)) != len(bundle_ids):
        errors.append("bundle IDs are not unique")
    memberships = [set(bundle.customer_ids) for bundle in bundles]
    seen: Set[int] = set()
    for membership in memberships:
        if seen.intersection(membership):
            errors.append("bundle memberships overlap")
        seen.update(membership)
    removed = state.metadata.get("cascade_removed")
    if not isinstance(removed, list) or set(int(customer) for customer in removed) != seen:
        errors.append("cascade_removed does not equal the bundle membership union")
    if not seen.issubset(set(int(customer) for customer in state.unassigned)):
        errors.append("a bundle customer is not unassigned in the destroyed State")
    for bundle in bundles:
        errors.extend(_validate_bundle_snapshot(bundle, contract, state))
    return (None, errors) if errors else (bundles, [])


def _external_structure_projection(
    state: TVDState,
    bundle_customers: Set[int],
) -> Tuple[object, ...]:
    outside_modes = tuple(
        (int(customer), str(mode))
        for customer, mode in sorted(state.service_mode.items())
        if int(customer) not in bundle_customers
    )
    normalized_routes = tuple(
        (
            str(van_id),
            tuple(int(node) for node in route if int(node) not in bundle_customers),
        )
        for van_id, route in sorted(state.van_routes.items())
    )
    outside_sorties = tuple(
        _sortie_structural_identity(sortie)
        for sortie in state.drone_sorties
        if bundle_customers.isdisjoint(set(sortie_nodes(sortie)[1]))
    )
    outside_assignments = tuple(
        (int(customer), _stable_freeze(assignment))
        for customer, assignment in sorted(state.order_assignment.items())
        if int(customer) not in bundle_customers
    )
    return (
        int(state.selected_transshipment),
        tuple(int(node) for node in state.truck_route),
        _stable_freeze(state.tractor_routes),
        _stable_freeze(state.container_routes),
        normalized_routes,
        outside_sorties,
        outside_modes,
        outside_assignments,
        _stable_freeze(state.container_assignment),
        _stable_freeze(state.van_home),
        _stable_freeze(state.drone_initial_carrier),
        _stable_freeze(state.drone_home_warehouse),
    )


def _candidate_changes_only_affected_scope(
    before: TVDState,
    candidate: TVDState,
    bundle: CascadeBundleSnapshot,
) -> bool:
    bundle_customers = set(bundle.customer_ids)
    affected_vans = {snapshot.van_id for snapshot in bundle.affected_route_segments}
    all_vans = set(before.van_routes) | set(candidate.van_routes)
    for van_id in all_vans - affected_vans:
        if before.van_routes.get(van_id) != candidate.van_routes.get(van_id):
            return False
    for customer in bundle_customers:
        for van_id, route in candidate.van_routes.items():
            if customer in route and van_id not in affected_vans:
                return False
    for sortie in candidate.drone_sorties:
        _, customers, _ = sortie_nodes(sortie)
        if bundle_customers.intersection(customers):
            if not isinstance(sortie, dict):
                return False
            launch_van = str(sortie.get("launch_van_id", ""))
            recovery_van = str(sortie.get("recovery_van_id", launch_van))
            if launch_van not in affected_vans or recovery_van not in affected_vans:
                return False
    return _external_structure_projection(before, bundle_customers) == (
        _external_structure_projection(candidate, bundle_customers)
    )


def _validate_cascade_candidate(
    state: TVDState,
    *,
    bundle_customers: Set[int],
    allowed_unassigned: Set[int],
    data: InstanceData,
    config: TVDConfig,
    metrics: Dict[str, object],
) -> Tuple[bool, List[str]]:
    """Thin partial-validation wrapper around the canonical full checker."""

    metrics["checker_call_count"] = int(metrics.get("checker_call_count", 0)) + 1
    _, violations = check_solution_feasible(state, data, config)
    actual_unassigned = set(int(customer) for customer in state.unassigned)
    retained: List[str] = []
    exact_missing = f"unassigned customers remain: {sorted(state.unassigned)}"
    for violation in violations:
        if (
            violation == exact_missing
            and actual_unassigned == allowed_unassigned
            and bundle_customers.isdisjoint(actual_unassigned)
        ):
            continue
        retained.append(violation)
    if actual_unassigned != allowed_unassigned:
        retained.append(
            "candidate changed the explicit allowed-unassigned customer set"
        )
    if bundle_customers.intersection(actual_unassigned):
        retained.append("bundle customer remains unassigned")
    return not retained, retained


def _restore_snapshot_strategy_state(
    state: TVDState,
    bundle: CascadeBundleSnapshot,
    metrics: Dict[str, object],
) -> Optional[TVDState]:
    candidate = _cascade_state_copy(state, metrics)
    if any(customer not in candidate.unassigned for customer in bundle.customer_ids):
        return None

    van_services = [
        service
        for service in bundle.customer_service_snapshots
        if service.service_mode == "van"
    ]
    van_services.sort(
        key=lambda service: (
            service.van_route_positions[0].van_id,
            service.van_route_positions[0].route_position,
            service.customer_id,
        )
    )
    for service in van_services:
        position = service.van_route_positions[0]
        route = candidate.van_routes.get(position.van_id)
        if route is None or len(route) < 2:
            return None
        insert_at = min(max(1, position.route_position), len(route) - 1)
        route.insert(insert_at, int(service.customer_id))
        candidate.service_mode[int(service.customer_id)] = "van"
        candidate.clean_unassigned(int(service.customer_id))
    candidate.sync_primary_van_route()

    links = {item.sortie_id: item for item in bundle.launch_recovery_snapshots}
    carriers = {item.sortie_id: item for item in bundle.carrier_transfer_snapshots}
    for snapshot in sorted(
        bundle.removed_drone_subroutes,
        key=lambda item: (item.source_sortie_index, item.sortie_id),
    ):
        link = links.get(snapshot.sortie_id)
        carrier = carriers.get(snapshot.sortie_id)
        if link is None or carrier is None or snapshot.drone_id is None:
            return None
        if carrier.initial_carrier_van_id != candidate.drone_initial_carrier.get(
            snapshot.drone_id
        ):
            return None
        sortie = _make_drone_sortie(
            snapshot.launch_node,
            list(snapshot.customer_ids),
            snapshot.recovery_node,
            drone_id=snapshot.drone_id,
            launch_van_id=str(link.launch_van_id or ""),
            recovery_van_id=str(link.recovery_van_id or ""),
        )
        sortie["launch_position"] = int(link.launch_position or 0)
        sortie["recovery_position"] = int(link.recovery_position or 0)
        candidate.drone_sorties.append(sortie)
        for customer in snapshot.customer_ids:
            candidate.service_mode[int(customer)] = "drone"
            candidate.clean_unassigned(int(customer))
    return candidate


def _van_block_strategy_states(
    state: TVDState,
    bundle: CascadeBundleSnapshot,
    data: InstanceData,
    metrics: Dict[str, object],
) -> List[TVDState]:
    customers = tuple(int(customer) for customer in bundle.dependency_order)
    if any(data.is_high_floor.get(customer, False) for customer in customers):
        return []
    states: List[TVDState] = []
    for snapshot in sorted(
        bundle.affected_route_segments,
        key=lambda item: (item.van_id, item.start_position, item.end_position),
    ):
        route = state.van_routes.get(snapshot.van_id)
        if route is None or len(route) < 2 or snapshot.start_position < 0:
            continue
        first = max(1, min(snapshot.start_position, len(route) - 1))
        last = max(first, min(snapshot.end_position, len(route) - 1))
        for insert_at in range(first, last + 1):
            candidate = _cascade_state_copy(state, metrics)
            candidate.van_routes[snapshot.van_id][insert_at:insert_at] = list(customers)
            candidate.sync_primary_van_route()
            for customer in customers:
                candidate.service_mode[customer] = "van"
                candidate.clean_unassigned(customer)
            states.append(candidate)
    return states


def _drone_bundle_strategy_states(
    state: TVDState,
    bundle: CascadeBundleSnapshot,
    data: InstanceData,
    config: TVDConfig,
    metrics: Dict[str, object],
) -> List[TVDState]:
    customers = list(int(customer) for customer in bundle.dependency_order)
    route_scope = {
        snapshot.van_id: set(int(node) for node in snapshot.route_nodes)
        for snapshot in bundle.affected_route_segments
    }
    if not route_scope:
        return []
    states: List[TVDState] = []
    for move in _enumerate_feasible_drone_moves_for_customers(
        customers, state, data, config
    ):
        sortie = move.sortie or {}
        launch_van = str(sortie.get("launch_van_id", ""))
        recovery_van = str(sortie.get("recovery_van_id", launch_van))
        launch, _, recovery = sortie_nodes(sortie)
        if launch_van not in route_scope or recovery_van not in route_scope:
            continue
        if int(launch) not in route_scope[launch_van]:
            continue
        if int(recovery) not in route_scope[recovery_van]:
            continue
        candidate = _cascade_state_copy(state, metrics)
        _apply_move(candidate, customers[0], _copy_move(move))
        states.append(candidate)
    return states


def _bundle_strategy_from_state(
    bundle: CascadeBundleSnapshot,
    state: TVDState,
    *,
    source_kind: str,
) -> BundleReconstructionStrategy:
    customer_set = set(bundle.customer_ids)
    affected_vans = sorted(
        {snapshot.van_id for snapshot in bundle.affected_route_segments}
    )
    relevant_sorties = sorted(
        (
            _sortie_structural_identity(sortie)
            for sortie in state.drone_sorties
            if customer_set.intersection(sortie_nodes(sortie)[1])
        ),
        key=repr,
    )
    launch_recovery = tuple(
        (
            identity[1],
            identity[2],
            identity[3],
            identity[5],
            identity[6],
            identity[7],
        )
        for identity in relevant_sorties
    )
    carrier_transfer = tuple(
        (
            identity[0],
            str(state.drone_initial_carrier.get(str(identity[0]), "")),
            identity[1],
            identity[5],
            identity[1] != identity[5],
        )
        for identity in relevant_sorties
    )
    return BundleReconstructionStrategy(
        bundle_id=bundle.bundle_id,
        customer_ids=tuple(int(customer) for customer in bundle.customer_ids),
        service_mode_reconstruction=tuple(
            (int(customer), str(state.service_mode.get(int(customer), "unassigned")))
            for customer in sorted(bundle.customer_ids)
        ),
        van_route_segment_reconstruction=tuple(
            (van_id, tuple(int(node) for node in state.van_routes.get(van_id, [])))
            for van_id in affected_vans
        ),
        drone_subroute_reconstruction=tuple(relevant_sorties),
        launch_recovery_reconstruction=launch_recovery,
        carrier_transfer_reconstruction=carrier_transfer,
        coordination_links=tuple(bundle.affected_structure_scope.coordination_edge_ids),
        resulting_state=state,
        source_kind=source_kind,
    )


def _enumerate_bundle_reconstruction_strategies(
    state: TVDState,
    bundle: CascadeBundleSnapshot,
    *,
    allowed_unassigned: Set[int],
    data: InstanceData,
    config: TVDConfig,
    metrics: Dict[str, object],
) -> Tuple[List[BundleReconstructionStrategy], Dict[str, object]]:
    """Construct a disclosed bundle-level Ω(B), without customer products.

    Implementation choice: the paper does not explicitly specify this detail.
    The family is the exact snapshot reconstruction, every affected-segment
    contiguous all-van reconstruction, and every scoped all-bundle drone
    reconstruction.  No per-customer Cartesian product, top-K, beam, or
    candidate truncation is used.
    """

    started = time.perf_counter()
    raw_states: List[Tuple[str, TVDState]] = []
    snapshot_state = _restore_snapshot_strategy_state(state, bundle, metrics)
    if snapshot_state is not None:
        raw_states.append(("snapshot", snapshot_state))
    raw_states.extend(
        ("van_block", candidate)
        for candidate in _van_block_strategy_states(state, bundle, data, metrics)
    )
    raw_states.extend(
        ("drone_bundle", candidate)
        for candidate in _drone_bundle_strategy_states(
            state, bundle, data, config, metrics
        )
    )

    feasible_strategies: List[BundleReconstructionStrategy] = []
    rejection_reasons: List[str] = []
    bundle_customers = set(bundle.customer_ids)
    for source_kind, candidate in raw_states:
        if not _candidate_changes_only_affected_scope(state, candidate, bundle):
            rejection_reasons.append(f"{source_kind}: outside affected scope")
            continue
        valid, violations = _validate_cascade_candidate(
            candidate,
            bundle_customers=bundle_customers,
            allowed_unassigned=allowed_unassigned,
            data=data,
            config=config,
            metrics=metrics,
        )
        if not valid:
            rejection_reasons.extend(
                f"{source_kind}: {violation}" for violation in violations
            )
            continue
        feasible_strategies.append(
            _bundle_strategy_from_state(
                bundle,
                candidate,
                source_kind=source_kind,
            )
        )

    unique: Dict[Tuple[object, ...], BundleReconstructionStrategy] = {}
    for strategy in feasible_strategies:
        identity = strategy.stable_identity()
        if identity not in unique:
            unique[identity] = strategy
    strategies = [unique[key] for key in sorted(unique, key=repr)]
    return strategies, {
        "bundle_id": bundle.bundle_id,
        "bundle_size": len(bundle.customer_ids),
        "affected_route_segment_count": len(bundle.affected_route_segments),
        "affected_drone_subroute_count": len(bundle.removed_drone_subroutes),
        "raw_bundle_strategy_count": len(raw_states),
        "feasible_bundle_strategy_count": len(feasible_strategies),
        "unique_bundle_strategy_count": len(strategies),
        "strategy_generation_sequence": [
            strategy.stable_identity() for strategy in strategies
        ],
        "rejection_reasons": rejection_reasons,
        "enumeration_time": time.perf_counter() - started,
    }


def _score_bundle_strategies(
    strategies: List[BundleReconstructionStrategy],
    data: InstanceData,
    config: TVDConfig,
    metrics: Dict[str, object],
) -> float:
    started = time.perf_counter()
    for strategy in strategies:
        metrics["objective_call_count"] = int(
            metrics.get("objective_call_count", 0)
        ) + 1
        # objective() invokes the canonical checker, even when its feasibility
        # result is served from the State cache.
        metrics["checker_call_count"] = int(metrics.get("checker_call_count", 0)) + 1
        total, _ = objective(strategy.resulting_state, data, config)
        strategy.objective_value = float(total)
    return time.perf_counter() - started


def _select_bundle_strategy(
    strategies: Iterable[BundleReconstructionStrategy],
) -> Optional[BundleReconstructionStrategy]:
    """Select by complete objective, then stable complete identity.

    Implementation choice: the paper does not specify exact objective ties.
    """

    scored = [strategy for strategy in strategies if strategy.objective_value is not None]
    if not scored:
        return None
    return min(
        scored,
        key=lambda strategy: (
            float(strategy.objective_value),
            strategy.stable_identity(),
        ),
    )


def _finish_cascade_result(
    state: TVDState,
    *,
    status: str,
    reason: Optional[str],
    metrics: Dict[str, object],
    bundle_rows: List[Dict[str, object]],
    started: float,
) -> TVDState:
    _clear_stale_cascade_metadata(state)
    metrics["bundle_repair_time"] = time.perf_counter() - started
    diagnostics = {
        "status": status,
        "reason": reason,
        "bundle_processing_sequence": [row["bundle_id"] for row in bundle_rows],
        "bundles": bundle_rows,
        **metrics,
        "maximum_reconstruction_depth": int(
            metrics.get("maximum_reconstruction_depth", 0)
        ),
        "lossy_pruning_used": False,
        "customer_compositional_product_used": False,
    }
    diagnostics["result_state_fingerprint"] = _state_business_fingerprint(state)
    state.metadata["cascade_repair_diagnostics"] = diagnostics
    return state


@removal_context_boundary
def cascade_repair(
    state: TVDState, rng: np.random.Generator, data: InstanceData, config: TVDConfig
) -> TVDState:
    enter_repair("cascade_repair")
    started = time.perf_counter()
    metrics: Dict[str, object] = {
        "state_copy_count": 0,
        "objective_call_count": 0,
        "checker_call_count": 0,
        "maximum_reconstruction_depth": 0,
        "enumeration_time": 0.0,
        "scoring_time": 0.0,
    }
    bundle_rows: List[Dict[str, object]] = []
    try:
        # rng is intentionally unused: bundle order and exact ties are stable.
        _ = rng
        repair_base = _cascade_state_copy(state, metrics)
        bundles, contract_errors = _validated_cascade_bundles(repair_base)
        if bundles is None:
            return _finish_cascade_result(
                repair_base,
                status="failure",
                reason="; ".join(contract_errors),
                metrics=metrics,
                bundle_rows=bundle_rows,
                started=started,
            )

        working_state = _cascade_state_copy(repair_base, metrics)
        all_bundle_customers = {
            int(customer)
            for bundle in bundles
            for customer in bundle.customer_ids
        }
        external_unassigned = set(int(customer) for customer in repair_base.unassigned) - (
            all_bundle_customers
        )

        # Implementation choice: the paper does not explicitly specify bundle
        # order. Preserve the stable order emitted by Cascade removal.
        for bundle_index, bundle in enumerate(bundles):
            later_bundle_customers = {
                int(customer)
                for later in bundles[bundle_index + 1 :]
                for customer in later.customer_ids
            }
            allowed_unassigned = external_unassigned | later_bundle_customers
            metrics["maximum_reconstruction_depth"] = max(
                int(metrics.get("maximum_reconstruction_depth", 0)),
                1,
            )
            strategies, row = _enumerate_bundle_reconstruction_strategies(
                working_state,
                bundle,
                allowed_unassigned=allowed_unassigned,
                data=data,
                config=config,
                metrics=metrics,
            )
            metrics["enumeration_time"] = float(metrics["enumeration_time"]) + float(
                row["enumeration_time"]
            )
            scoring_time = _score_bundle_strategies(
                strategies, data, config, metrics
            )
            metrics["scoring_time"] = float(metrics["scoring_time"]) + scoring_time
            row["scoring_time"] = scoring_time
            selected = _select_bundle_strategy(strategies)
            row["selected_strategy_identity"] = (
                selected.stable_identity() if selected is not None else None
            )
            row["selected_objective"] = (
                float(selected.objective_value)
                if selected is not None and selected.objective_value is not None
                else None
            )
            bundle_rows.append(row)
            if selected is None:
                # Empty Ω(B): fail the entire repair and discard earlier bundle
                # changes. No Global/Local/Regret/Best-mode fallback is called.
                return _finish_cascade_result(
                    repair_base,
                    status="failure",
                    reason=f"empty feasible strategy set for {bundle.bundle_id}",
                    metrics=metrics,
                    bundle_rows=bundle_rows,
                    started=started,
                )
            working_state = selected.resulting_state

        final_valid, final_violations = _validate_cascade_candidate(
            working_state,
            bundle_customers=all_bundle_customers,
            allowed_unassigned=external_unassigned,
            data=data,
            config=config,
            metrics=metrics,
        )
        if not final_valid:
            return _finish_cascade_result(
                repair_base,
                status="failure",
                reason="final validation failed: " + "; ".join(final_violations),
                metrics=metrics,
                bundle_rows=bundle_rows,
                started=started,
            )
        # Cascade deliberately performs no global sortie consolidation. The
        # selected strategy already reconstructs only the affected scope.
        return _finish_cascade_result(
            working_state,
            status="success",
            reason=None,
            metrics=metrics,
            bundle_rows=bundle_rows,
            started=started,
        )
    finally:
        exit_repair("cascade_repair")


DESTROY_OPERATORS: Dict[str, DestroyOperator] = {
    "random_customer_removal": random_customer_removal,
    "greedy_removal": greedy_removal,
    "related_customer_removal": related_customer_removal,
    "route_segment_removal": route_segment_removal,
    "drone_task_removal": drone_task_removal,
    "cascade_aware_removal": cascade_aware_removal,
    "switch_transshipment_operator": switch_transshipment_operator,
}

REPAIR_OPERATORS: Dict[str, RepairOperator] = {
    "greedy_van_repair": greedy_van_repair,
    "greedy_drone_repair": greedy_drone_repair,
    "best_mode_repair": best_mode_repair,
    "regret_repair": regret_repair,
    "cascade_repair": cascade_repair,
}


def repair_is_complete(state: TVDState, data: InstanceData, config: TVDConfig) -> bool:
    feasible, _ = check_solution_feasible(state, data, config)
    return feasible
