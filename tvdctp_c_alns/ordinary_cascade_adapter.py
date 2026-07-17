from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, is_dataclass
from typing import Dict, Iterable, List, MutableMapping, Optional, Set, Tuple

from removal_structural_context import (
    COMMON_PRODUCER_CAPABILITIES,
    RemovalStructuralContext,
    StructuralProjection,
    capture_structural_projection,
    structural_business_fingerprint,
    validate_removal_structural_context,
)
from state import (
    AffectedStructureScope,
    CarrierTransferSnapshot,
    CascadeBundleSnapshot,
    ContainerDecisionSnapshot,
    CustomerServiceSnapshot,
    DroneSubrouteSnapshot,
    LaunchRecoverySnapshot,
    TVDState,
    TruckWarehouseContextSnapshot,
    VanRoutePositionSnapshot,
    VanRouteSegmentSnapshot,
)


ORDINARY_CASCADE_ADAPTER_VERSION = 1
ORDINARY_CASCADE_SOURCES = (
    "random_customer_removal",
    "greedy_removal",
    "related_customer_removal",
)
ADAPTED_DEPENDENCY_ORDER_SEMANTICS = (
    "ordinary adapter v1 structural precedence"
)


class OrdinaryCascadeAdapterError(ValueError):
    """Controlled ordinary-context contract construction failure."""


@dataclass(frozen=True)
class AtomicStructuralEdge:
    edge_id: str
    edge_kind: str
    source_customer_id: int
    target_customer_id: int


def _canonical_json(value: object) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)  # type: ignore[arg-type]

    def encode_dataclass(item: object) -> object:
        if is_dataclass(item):
            return asdict(item)
        raise TypeError(f"unsupported canonical JSON value: {type(item).__name__}")

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=encode_dataclass,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _state_business_fingerprint(state: TVDState) -> str:
    return hashlib.sha256(repr(state.cache_signature()).encode("utf-8")).hexdigest()


def _structural_customer_order(
    context: RemovalStructuralContext,
    removed: Set[int],
) -> Tuple[int, ...]:
    order: List[int] = []

    def observe(customer: int) -> None:
        normalized = int(customer)
        if normalized in removed and normalized not in order:
            order.append(normalized)

    for route in context.pre_destroy_projection.van_routes:
        for node in route.nodes:
            observe(node)
    for sortie in context.pre_destroy_projection.drone_sortie_facts:
        observe(sortie.launch_node)
        for customer in sortie.customer_ids:
            observe(customer)
        observe(sortie.recovery_node)
    if set(order) != removed:
        missing = removed - set(order)
        raise OrdinaryCascadeAdapterError(
            "actual-R customer lacks a pre-destroy structural position: "
            f"{sorted(missing)}"
        )
    return tuple(order)


def _edge_id(kind: str, source: int, target: int) -> str:
    return (
        f"ordinary-adapter:v{ORDINARY_CASCADE_ADAPTER_VERSION}:"
        f"edge:{kind}:{int(source)}->{int(target)}"
    )


def _atomic_edges(
    context: RemovalStructuralContext,
    removed: Set[int],
) -> Tuple[AtomicStructuralEdge, ...]:
    edges: Dict[str, AtomicStructuralEdge] = {}

    def add(kind: str, source: int, target: int) -> None:
        source = int(source)
        target = int(target)
        if source == target or source not in removed or target not in removed:
            return
        edge = AtomicStructuralEdge(
            edge_id=_edge_id(kind, source, target),
            edge_kind=kind,
            source_customer_id=source,
            target_customer_id=target,
        )
        edges.setdefault(edge.edge_id, edge)

    pre = context.pre_destroy_projection
    for route in pre.van_routes:
        for source, target in zip(route.nodes, route.nodes[1:]):
            if source in removed and target in removed:
                add("contiguous-van", source, target)

    transfer_by_sortie = {
        fact.sortie_id: fact for fact in pre.carrier_transfer_facts
    }
    previous_by_drone: Dict[str, object] = {}
    for sortie in pre.drone_sortie_facts:
        actual_customers = tuple(
            customer for customer in sortie.customer_ids if customer in removed
        )
        for source, target in zip(actual_customers, actual_customers[1:]):
            add("same-sortie", source, target)
        if actual_customers:
            if sortie.launch_node in removed:
                add("launch-anchor", sortie.launch_node, actual_customers[0])
            if (
                sortie.recovery_node in removed
                and sortie.recovery_node != sortie.launch_node
            ):
                add("recovery-anchor", actual_customers[-1], sortie.recovery_node)

        if sortie.drone_id is not None:
            previous = previous_by_drone.get(sortie.drone_id)
            if previous is not None:
                previous_customers = tuple(
                    customer
                    for customer in previous.customer_ids  # type: ignore[attr-defined]
                    if customer in removed
                )
                previous_transfer = transfer_by_sortie.get(
                    previous.sortie_id  # type: ignore[attr-defined]
                )
                if (
                    previous_customers
                    and actual_customers
                    and previous_transfer is not None
                    and previous_transfer.transferred is True
                    and previous_transfer.recovery_carrier_van_id
                    == sortie.launch_van_id
                ):
                    add(
                        "carrier-transfer",
                        previous_customers[-1],
                        actual_customers[0],
                    )
            previous_by_drone[sortie.drone_id] = sortie

    prefix = "node:"
    for fact in pre.coordination_edge_facts:
        if fact.edge_kind != "launch-recovery-order":
            continue
        if not (
            fact.source_entity_id.startswith(prefix)
            and fact.target_entity_id.startswith(prefix)
        ):
            continue
        try:
            source = int(fact.source_entity_id[len(prefix) :])
            target = int(fact.target_entity_id[len(prefix) :])
        except ValueError:
            continue
        add("explicit-coordination", source, target)
    return tuple(edges.values())


def _partition_and_order(
    removed_order: Tuple[int, ...],
    edges: Tuple[AtomicStructuralEdge, ...],
) -> Tuple[Tuple[Tuple[int, ...], ...], Tuple[Tuple[int, ...], ...]]:
    rank = {customer: index for index, customer in enumerate(removed_order)}
    neighbors: Dict[int, Set[int]] = {customer: set() for customer in removed_order}
    directed: Dict[int, Set[int]] = {customer: set() for customer in removed_order}
    indegree: Dict[int, int] = {customer: 0 for customer in removed_order}
    for edge in edges:
        source = edge.source_customer_id
        target = edge.target_customer_id
        neighbors[source].add(target)
        neighbors[target].add(source)
        if target not in directed[source]:
            directed[source].add(target)
            indegree[target] += 1

    components: List[Tuple[int, ...]] = []
    visited: Set[int] = set()
    for start in removed_order:
        if start in visited:
            continue
        pending = [start]
        visited.add(start)
        component: List[int] = []
        while pending:
            current = pending.pop(0)
            component.append(current)
            for neighbor in sorted(neighbors[current], key=rank.__getitem__):
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        components.append(tuple(sorted(component, key=rank.__getitem__)))

    dependency_orders: List[Tuple[int, ...]] = []
    for component in components:
        membership = set(component)
        local_indegree = {
            customer: sum(
                1
                for source in membership
                if customer in directed[source]
            )
            for customer in component
        }
        ready = sorted(
            (customer for customer in component if local_indegree[customer] == 0),
            key=rank.__getitem__,
        )
        order: List[int] = []
        while ready:
            customer = ready.pop(0)
            order.append(customer)
            for target in sorted(directed[customer] & membership, key=rank.__getitem__):
                local_indegree[target] -= 1
                if local_indegree[target] == 0:
                    ready.append(target)
                    ready.sort(key=rank.__getitem__)
        if len(order) != len(component):
            raise OrdinaryCascadeAdapterError(
                "ordinary adapter structural precedence graph contains a cycle"
            )
        dependency_orders.append(tuple(order))
    return tuple(components), tuple(dependency_orders)


def _optional_int(value: object) -> Optional[int]:
    return None if value is None else int(value)


def _optional_float(value: object) -> Optional[float]:
    return None if value is None else float(value)


def _optional_str(value: object) -> Optional[str]:
    return None if value is None else str(value)


def _build_snapshot(
    context: RemovalStructuralContext,
    destroyed_state: TVDState,
    component: Tuple[int, ...],
    dependency_order: Tuple[int, ...],
    edges: Tuple[AtomicStructuralEdge, ...],
    *,
    bundle_index: int,
    destroy_call_id: str,
) -> CascadeBundleSnapshot:
    pre = context.pre_destroy_projection
    customer_set = set(component)
    route_by_id = {route.van_id: route for route in pre.van_routes}
    service_by_customer = {
        fact.customer_id: fact for fact in pre.customer_service_facts
    }
    carrier_by_drone = {
        fact.drone_id: fact for fact in pre.carrier_relation_facts
    }

    service_snapshots: List[CustomerServiceSnapshot] = []
    affected_vans: Set[str] = set()
    affected_nodes: Set[int] = set(component)
    affected_containers: Set[int] = set()
    for customer in dependency_order:
        fact = service_by_customer.get(customer)
        if fact is None or fact.service_mode not in {"van", "drone"}:
            raise OrdinaryCascadeAdapterError(
                f"customer {customer} lacks a valid pre-destroy service fact"
            )
        positions = tuple(
            VanRoutePositionSnapshot(
                van_id=van_id,
                route_position=position,
                warehouse_id=(
                    route_by_id[van_id].warehouse_id
                    if van_id in route_by_id
                    else None
                ),
            )
            for van_id, position in fact.van_route_positions
        )
        if fact.service_mode == "van" and len(positions) != 1:
            raise OrdinaryCascadeAdapterError(
                f"van customer {customer} lacks exactly one source route position"
            )
        affected_vans.update(position.van_id for position in positions)
        if fact.container_id is not None:
            affected_containers.add(fact.container_id)
        service_snapshots.append(
            CustomerServiceSnapshot(
                customer_id=customer,
                service_mode=fact.service_mode,
                van_route_positions=positions,
                container_id=fact.container_id,
                assigned_transshipment=fact.assigned_transshipment,
            )
        )

    related_sorties = []
    for sortie_index, sortie in enumerate(pre.drone_sortie_facts):
        related = bool(customer_set.intersection(sortie.customer_ids)) or (
            sortie.launch_node in customer_set or sortie.recovery_node in customer_set
        )
        if not related:
            continue
        if not set(sortie.customer_ids).issubset(customer_set):
            raise OrdinaryCascadeAdapterError(
                f"partial actual-R sortie is not representable: {sortie.sortie_id}"
            )
        related_sorties.append((sortie_index, sortie))
        affected_nodes.update((sortie.launch_node, sortie.recovery_node))
        if sortie.launch_van_id is not None:
            affected_vans.add(sortie.launch_van_id)
        if sortie.recovery_van_id is not None:
            affected_vans.add(sortie.recovery_van_id)

    drone_snapshots: List[DroneSubrouteSnapshot] = []
    link_snapshots: List[LaunchRecoverySnapshot] = []
    carrier_snapshots: List[CarrierTransferSnapshot] = []
    for sortie_index, sortie in related_sorties:
        drone_snapshots.append(
            DroneSubrouteSnapshot(
                sortie_id=sortie.sortie_id,
                source_sortie_index=sortie_index,
                drone_id=sortie.drone_id,
                customer_ids=sortie.customer_ids,
                launch_node=sortie.launch_node,
                recovery_node=sortie.recovery_node,
            )
        )
        link_snapshots.append(
            LaunchRecoverySnapshot(
                sortie_id=sortie.sortie_id,
                launch_van_id=sortie.launch_van_id,
                recovery_van_id=sortie.recovery_van_id,
                launch_node=sortie.launch_node,
                recovery_node=sortie.recovery_node,
                launch_position=sortie.launch_position,
                recovery_position=sortie.recovery_position,
                same_van_recovery=(
                    sortie.launch_van_id == sortie.recovery_van_id
                    if sortie.launch_van_id is not None
                    and sortie.recovery_van_id is not None
                    else None
                ),
            )
        )
        initial = (
            carrier_by_drone.get(sortie.drone_id)
            if sortie.drone_id is not None
            else None
        )
        carrier_snapshots.append(
            CarrierTransferSnapshot(
                sortie_id=sortie.sortie_id,
                drone_id=sortie.drone_id,
                initial_carrier_van_id=(
                    initial.initial_carrier_van_id if initial is not None else None
                ),
                launch_carrier_van_id=sortie.launch_van_id,
                recovery_carrier_van_id=sortie.recovery_van_id,
                carrier_transfer=(
                    sortie.launch_van_id != sortie.recovery_van_id
                    if sortie.launch_van_id is not None
                    and sortie.recovery_van_id is not None
                    else None
                ),
            )
        )

    route_snapshots: List[VanRouteSegmentSnapshot] = []
    route_segment_ids: List[str] = []
    for van_id in sorted(affected_vans):
        route = route_by_id.get(van_id)
        if route is None:
            raise OrdinaryCascadeAdapterError(
                f"affected van {van_id} lacks a pre-destroy route"
            )
        positions = tuple(
            position
            for position, node in enumerate(route.nodes)
            if node in affected_nodes
        )
        if positions:
            start = max(0, min(positions) - 1)
            end = min(len(route.nodes) - 1, max(positions) + 1)
            route_nodes = route.nodes[start : end + 1]
            route_id = f"van:{van_id}:{start}-{end}"
        else:
            start = -1
            end = -1
            route_nodes = ()
            route_id = f"van:{van_id}:unresolved"
        route_snapshots.append(
            VanRouteSegmentSnapshot(
                van_id=van_id,
                warehouse_id=route.warehouse_id,
                start_position=start,
                end_position=end,
                route_nodes=tuple(route_nodes),
                affected_positions=positions,
            )
        )
        route_segment_ids.append(route_id)

    container_decisions: List[ContainerDecisionSnapshot] = []
    for container_id in sorted(affected_containers):
        route = destroyed_state.container_routes.get(container_id, {})
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

    sortie_ids = tuple(item.sortie_id for item in drone_snapshots)
    link_ids = tuple(
        edge
        for sortie_id in sortie_ids
        for edge in (f"{sortie_id}:launch", f"{sortie_id}:recovery")
    )
    carrier_ids = tuple(f"{sortie_id}:carrier" for sortie_id in sortie_ids)
    native_coordination = tuple(
        edge
        for sortie_id in sortie_ids
        for edge in (
            f"{sortie_id}:truck-van-context",
            f"{sortie_id}:van-drone-launch",
            f"{sortie_id}:van-drone-recovery",
        )
    )
    atomic_ids = tuple(
        edge.edge_id
        for edge in edges
        if edge.source_customer_id in customer_set
        and edge.target_customer_id in customer_set
    )
    boundary_ids = tuple(
        f"ordinary-adapter:v{ORDINARY_CASCADE_ADAPTER_VERSION}:"
        f"external-boundary:customer:{customer}"
        for customer in context.external_boundary_entities.customer_ids
    )
    scope = AffectedStructureScope(
        truck_context_ids=(
            f"selected_transshipment:{int(destroyed_state.selected_transshipment)}",
            *(
                f"container:{container_id}"
                for container_id in sorted(affected_containers)
            ),
        ),
        van_route_segment_ids=tuple(route_segment_ids),
        drone_subroute_ids=sortie_ids,
        launch_recovery_link_ids=link_ids,
        carrier_link_ids=carrier_ids,
        coordination_edge_ids=native_coordination + atomic_ids + boundary_ids,
    )
    return CascadeBundleSnapshot(
        schema_version=1,
        bundle_id=(
            f"ordinary:{context.source_destroy_operator}:"
            f"{context.context_id[:20]}:bundle:{bundle_index:04d}"
        ),
        source_operator=context.source_destroy_operator,
        source_destroy_call_id=destroy_call_id,
        source_state_fingerprint=context.pre_destroy_structural_fingerprint,
        customer_ids=dependency_order,
        dependency_order=dependency_order,
        dependency_order_semantics=ADAPTED_DEPENDENCY_ORDER_SEMANTICS,
        customer_service_snapshots=tuple(service_snapshots),
        affected_route_segments=tuple(route_snapshots),
        removed_drone_subroutes=tuple(drone_snapshots),
        launch_recovery_snapshots=tuple(link_snapshots),
        carrier_transfer_snapshots=tuple(carrier_snapshots),
        truck_warehouse_context=TruckWarehouseContextSnapshot(
            selected_transshipment=int(destroyed_state.selected_transshipment),
            container_decisions=tuple(container_decisions),
        ),
        affected_structure_scope=scope,
    )


def validate_ordinary_context_for_cascade_adapter(
    context: RemovalStructuralContext,
    destroyed_state: TVDState,
) -> None:
    validate_removal_structural_context(context)
    if context.source_destroy_operator not in ORDINARY_CASCADE_SOURCES:
        raise OrdinaryCascadeAdapterError(
            f"unsupported ordinary adapter source: {context.source_destroy_operator}"
        )
    if context.producer_capabilities != COMMON_PRODUCER_CAPABILITIES:
        raise OrdinaryCascadeAdapterError("ordinary producer capability mismatch")
    current_projection = capture_structural_projection(destroyed_state)
    current_fingerprint = structural_business_fingerprint(current_projection)
    if current_fingerprint != context.post_destroy_structural_fingerprint:
        raise OrdinaryCascadeAdapterError(
            "destroyed State post structural fingerprint mismatch"
        )
    removed = set(context.actually_unassigned_customer_ids)
    transition = set(current_projection.unassigned) - set(
        context.pre_destroy_projection.unassigned
    )
    if transition != removed:
        raise OrdinaryCascadeAdapterError(
            "destroyed State actual-unassigned transition mismatch"
        )
    if removed.intersection(context.external_boundary_entities.customer_ids):
        raise OrdinaryCascadeAdapterError(
            "actual-R overlaps the external boundary"
        )
    if not removed:
        raise OrdinaryCascadeAdapterError("ordinary adapter actual-R is empty")


def adapt_removal_context_to_cascade_bundles(
    context: RemovalStructuralContext,
    destroyed_state: TVDState,
    *,
    diagnostics: Optional[MutableMapping[str, object]] = None,
) -> Tuple[CascadeBundleSnapshot, ...]:
    """Convert objective-free removal facts into the existing native type."""

    started = time.perf_counter()
    validation_started = time.perf_counter()
    validate_ordinary_context_for_cascade_adapter(context, destroyed_state)
    validation_time = time.perf_counter() - validation_started
    construction_started = time.perf_counter()
    removed = set(context.actually_unassigned_customer_ids)
    removed_order = _structural_customer_order(context, removed)
    edges = _atomic_edges(context, removed)
    components, dependency_orders = _partition_and_order(removed_order, edges)
    contract_revision = _digest(
        {
            "adapter_version": ORDINARY_CASCADE_ADAPTER_VERSION,
            "source_operator": context.source_destroy_operator,
            "source_context_id": context.context_id,
            "actual_r": removed_order,
            "components": components,
            "dependency_orders": dependency_orders,
            "atomic_edges": edges,
        }
    )
    destroy_call_id = (
        f"ordinary-adapter:v{ORDINARY_CASCADE_ADAPTER_VERSION}:"
        f"{context.context_id}:{contract_revision}"
    )
    bundles = tuple(
        _build_snapshot(
            context,
            destroyed_state,
            component,
            dependency_order,
            edges,
            bundle_index=index,
            destroy_call_id=destroy_call_id,
        )
        for index, (component, dependency_order) in enumerate(
            zip(components, dependency_orders)
        )
    )
    union = {customer for bundle in bundles for customer in bundle.customer_ids}
    if union != removed:
        raise OrdinaryCascadeAdapterError("adapted bundle union does not equal actual-R")
    seen: Set[int] = set()
    for bundle in bundles:
        membership = set(bundle.customer_ids)
        if seen.intersection(membership):
            raise OrdinaryCascadeAdapterError("adapted bundle memberships overlap")
        seen.update(membership)
    construction_time = time.perf_counter() - construction_started
    if diagnostics is not None:
        diagnostics.update(
            {
                "ordinary_adapter_version": ORDINARY_CASCADE_ADAPTER_VERSION,
                "ordinary_adapter_source": context.source_destroy_operator,
                "ordinary_adapter_context_id": context.context_id,
                "ordinary_adapter_call_count": 1,
                "context_validation_time": validation_time,
                "adapter_time": time.perf_counter() - started,
                "bundle_construction_time": construction_time,
                "atomic_edge_ids": tuple(edge.edge_id for edge in edges),
                "adapted_partition": tuple(
                    bundle.customer_ids for bundle in bundles
                ),
                "adapted_dependency_order": tuple(
                    bundle.dependency_order for bundle in bundles
                ),
            }
        )
    return bundles


def install_adapted_cascade_contract(
    state: TVDState,
    context: RemovalStructuralContext,
    bundles: Iterable[CascadeBundleSnapshot],
) -> None:
    snapshots = tuple(bundles)
    if not snapshots:
        raise OrdinaryCascadeAdapterError("adapted contract has no bundles")
    destroy_call_ids = {bundle.source_destroy_call_id for bundle in snapshots}
    if len(destroy_call_ids) != 1:
        raise OrdinaryCascadeAdapterError("adapted bundles disagree on destroy call ID")
    removed = set(context.actually_unassigned_customer_ids)
    union = {customer for bundle in snapshots for customer in bundle.customer_ids}
    if union != removed:
        raise OrdinaryCascadeAdapterError("adapted contract union mismatch")
    state.metadata["cascade_removed"] = [
        customer for bundle in snapshots for customer in bundle.dependency_order
    ]
    state.metadata["cascade_bundles"] = list(snapshots)
    state.metadata["cascade_contract"] = {
        "schema_version": 1,
        "source_operator": context.source_destroy_operator,
        "destroy_call_id": next(iter(destroy_call_ids)),
        "source_state_fingerprint": context.pre_destroy_structural_fingerprint,
        "destroyed_state_fingerprint": _state_business_fingerprint(state),
        "bundle_ids": tuple(bundle.bundle_id for bundle in snapshots),
        "bundle_fingerprints": tuple(
            bundle.contract_fingerprint() for bundle in snapshots
        ),
        "captured_before_removal": True,
        "ordinary_adapter_version": ORDINARY_CASCADE_ADAPTER_VERSION,
        "source_context_id": context.context_id,
        "post_structural_fingerprint": context.post_destroy_structural_fingerprint,
        "actual_unassigned_customer_ids": context.actually_unassigned_customer_ids,
        "external_boundary_customer_ids": (
            context.external_boundary_entities.customer_ids
        ),
        "external_boundary_projection_fingerprint": _digest(
            context.external_boundary_projection
        ),
    }


def projection_external_boundary_business_projection(
    projection: StructuralProjection,
    excluded_customers: Iterable[int],
) -> Tuple[object, ...]:
    excluded = {int(customer) for customer in excluded_customers}
    modes = tuple(
        (fact.customer_id, fact.service_mode, fact.unassigned)
        for fact in projection.customer_service_facts
        if fact.customer_id not in excluded
    )
    routes = tuple(
        (
            route.van_id,
            tuple(node for node in route.nodes if node not in excluded),
        )
        for route in projection.van_routes
    )
    sorties = tuple(
        fact
        for fact in projection.drone_sortie_facts
        if excluded.isdisjoint(fact.customer_ids)
    )
    return modes, routes, sorties
