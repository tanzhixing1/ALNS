from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from functools import wraps
from typing import Callable, Dict, Iterable, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from state import TVDState


ACTIVE_REMOVAL_CONTEXT_KEY = "_active_removal_structural_context"
REMOVAL_CONTEXT_SCHEMA_VERSION = 1
STRUCTURAL_CONTEXT_VERSION = 1

COMMON_PRODUCER_CAPABILITIES = (
    "structural_context_v1",
    "immutable_pre_projection",
    "authoritative_post_diff",
    "selection_order",
    "deletion_order",
    "mutation_footprint",
    "external_boundary_facts",
)
CASCADE_PRODUCER_CAPABILITIES = (
    "cascade_dependency_trace",
    "cascade_native_partition",
    "cascade_native_order",
)


class RemovalContextContractError(ValueError):
    pass


class RemovalContextLifecycleError(RuntimeError):
    pass


def _canonical_json(value: object) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)  # type: ignore[arg-type]
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _freeze(value: object) -> object:
    """Return a stable, recursively immutable representation."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        rows = [
            (type(key).__name__, str(key), _freeze(item))
            for key, item in value.items()
        ]
        return ("map", tuple(sorted(rows, key=lambda row: (row[0], row[1]))))
    if isinstance(value, (list, tuple)):
        return ("sequence", tuple(_freeze(item) for item in value))
    if isinstance(value, (set, frozenset)):
        items = [_freeze(item) for item in value]
        return ("set", tuple(sorted(items, key=_canonical_json)))
    raise RemovalContextContractError(
        f"unsupported structural projection value: {type(value).__name__}"
    )


@dataclass(frozen=True)
class VanRouteFact:
    van_id: str
    warehouse_id: Optional[int]
    nodes: Tuple[int, ...]


@dataclass(frozen=True)
class RoutePositionFact:
    van_id: str
    route_position: int
    node_id: int
    predecessor_node: Optional[int]
    successor_node: Optional[int]


@dataclass(frozen=True)
class RouteSegmentFact:
    segment_id: str
    van_id: str
    start_position: int
    end_position: int
    start_node: int
    end_node: int


@dataclass(frozen=True)
class DroneSortieFact:
    sortie_id: str
    source_occurrence: int
    drone_id: Optional[str]
    customer_ids: Tuple[int, ...]
    launch_node: int
    recovery_node: int
    launch_van_id: Optional[str]
    recovery_van_id: Optional[str]
    launch_position: Optional[int]
    recovery_position: Optional[int]


@dataclass(frozen=True)
class LaunchRecoveryFact:
    sortie_id: str
    launch_link_id: str
    recovery_link_id: str
    launch_node: int
    recovery_node: int
    launch_van_id: Optional[str]
    recovery_van_id: Optional[str]
    launch_position: Optional[int]
    recovery_position: Optional[int]


@dataclass(frozen=True)
class CarrierRelationFact:
    relation_id: str
    drone_id: str
    initial_carrier_van_id: Optional[str]
    current_carrier_van_id: Optional[str]


@dataclass(frozen=True)
class CarrierTransferFact:
    transfer_id: str
    sortie_id: str
    drone_id: Optional[str]
    launch_carrier_van_id: Optional[str]
    recovery_carrier_van_id: Optional[str]
    transferred: Optional[bool]


@dataclass(frozen=True)
class CoordinationEdgeFact:
    edge_id: str
    edge_kind: str
    source_entity_id: str
    target_entity_id: str


@dataclass(frozen=True)
class CustomerServiceFact:
    customer_id: int
    service_mode: Optional[str]
    unassigned: bool
    van_route_positions: Tuple[Tuple[str, int], ...]
    drone_sortie_ids: Tuple[str, ...]
    container_id: Optional[int]
    assigned_transshipment: Optional[int]


@dataclass(frozen=True)
class StructuralProjection:
    schema_version: int
    port_node: int
    truck_depot_node: int
    transshipment_nodes: Tuple[int, ...]
    selected_transshipment: int
    container_origin: int
    truck_route: Tuple[int, ...]
    tractor_routes: object
    tractor_home: object
    trailer_home: object
    container_routes: object
    van_routes: Tuple[VanRouteFact, ...]
    route_position_facts: Tuple[RoutePositionFact, ...]
    route_segment_facts: Tuple[RouteSegmentFact, ...]
    drone_sortie_facts: Tuple[DroneSortieFact, ...]
    launch_recovery_facts: Tuple[LaunchRecoveryFact, ...]
    carrier_relation_facts: Tuple[CarrierRelationFact, ...]
    carrier_transfer_facts: Tuple[CarrierTransferFact, ...]
    coordination_edge_facts: Tuple[CoordinationEdgeFact, ...]
    customer_service_facts: Tuple[CustomerServiceFact, ...]
    order_assignment: object
    container_assignment: object
    van_home: object
    drone_initial_carrier: object
    drone_home_warehouse: object
    service_mode: Tuple[Tuple[int, str], ...]
    unassigned: Tuple[int, ...]
    business_metadata: object

    def canonical_json(self) -> str:
        return _canonical_json(self)


@dataclass(frozen=True)
class RouteMutationFact:
    van_id: str
    pre_start_position: int
    pre_end_position: int
    pre_nodes: Tuple[int, ...]
    post_start_position: int
    post_end_position: int
    post_nodes: Tuple[int, ...]
    predecessor_boundary_node: Optional[int]
    successor_boundary_node: Optional[int]


@dataclass(frozen=True)
class SortieSequenceMutation:
    sortie_id: str
    pre_customer_ids: Tuple[int, ...]
    post_customer_ids: Tuple[int, ...]


@dataclass(frozen=True)
class ServiceTransitionFact:
    customer_id: int
    pre_service_mode: Optional[str]
    post_service_mode: Optional[str]
    pre_unassigned: bool
    post_unassigned: bool


@dataclass(frozen=True)
class MutationFootprint:
    mutated_van_route_ids: Tuple[str, ...]
    mutated_contiguous_route_intervals: Tuple[RouteMutationFact, ...]
    removed_or_replaced_sortie_ids: Tuple[str, ...]
    added_or_replaced_sortie_ids: Tuple[str, ...]
    mutated_sortie_customer_sequences: Tuple[SortieSequenceMutation, ...]
    mutated_launch_recovery_link_ids: Tuple[str, ...]
    mutated_carrier_relation_ids: Tuple[str, ...]
    mutated_coordination_edge_ids: Tuple[str, ...]
    service_mode_transitions: Tuple[ServiceTransitionFact, ...]
    unassigned_transitions: Tuple[ServiceTransitionFact, ...]
    external_customers_touched: Tuple[int, ...]
    external_resources_touched: Tuple[str, ...]


@dataclass(frozen=True)
class ExternalBoundaryEntities:
    customer_ids: Tuple[int, ...]
    resource_ids: Tuple[str, ...]
    structural_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class ProducerDescriptor:
    source_destroy_operator: str
    schema_versions: Tuple[int, ...]
    structural_context_version: int
    capabilities: Tuple[str, ...]


PRODUCER_DESCRIPTORS: Dict[str, ProducerDescriptor] = {
    name: ProducerDescriptor(
        source_destroy_operator=name,
        schema_versions=(REMOVAL_CONTEXT_SCHEMA_VERSION,),
        structural_context_version=STRUCTURAL_CONTEXT_VERSION,
        capabilities=COMMON_PRODUCER_CAPABILITIES
        + (CASCADE_PRODUCER_CAPABILITIES if name == "cascade_aware_removal" else ()),
    )
    for name in (
        "random_customer_removal",
        "greedy_removal",
        "related_customer_removal",
        "cascade_aware_removal",
    )
}


@dataclass(frozen=True)
class RemovalStructuralContext:
    schema_version: int
    structural_context_version: int
    context_id: str
    source_destroy_operator: str
    producer_capabilities: Tuple[str, ...]
    pre_destroy_structural_fingerprint: str
    post_destroy_structural_fingerprint: str
    selected_removed_customer_ids: Tuple[int, ...]
    actually_unassigned_customer_ids: Tuple[int, ...]
    removal_order: Tuple[int, ...]
    customer_selection_order: Tuple[int, ...]
    deletion_attempt_order: Tuple[int, ...]
    actual_unassignment_order: Tuple[int, ...]
    pre_destroy_projection: StructuralProjection
    post_destroy_projection: StructuralProjection
    customer_service_facts: Tuple[CustomerServiceFact, ...]
    route_position_facts: Tuple[RoutePositionFact, ...]
    route_segment_facts: Tuple[RouteSegmentFact, ...]
    drone_sortie_facts: Tuple[DroneSortieFact, ...]
    launch_recovery_facts: Tuple[LaunchRecoveryFact, ...]
    carrier_transfer_facts: Tuple[CarrierTransferFact, ...]
    coordination_edge_facts: Tuple[CoordinationEdgeFact, ...]
    mutation_footprint: MutationFootprint
    external_boundary_entities: ExternalBoundaryEntities
    external_boundary_projection: Tuple[CustomerServiceFact, ...]
    cascade_dependency_trace: Tuple[Tuple[int, int], ...] = ()
    cascade_native_partition_evidence: Tuple[Tuple[int, ...], ...] = ()
    cascade_native_dependency_order: Tuple[Tuple[int, ...], ...] = ()

    @property
    def pre_destroy_business_fingerprint(self) -> str:
        return self.pre_destroy_structural_fingerprint

    @property
    def post_destroy_business_fingerprint(self) -> str:
        return self.post_destroy_structural_fingerprint

    def canonical_json(self) -> str:
        return _canonical_json(self)


def _optional_int(value: object) -> Optional[int]:
    return None if value is None else int(value)


def _optional_str(value: object) -> Optional[str]:
    return None if value is None else str(value)


def _sortie_values(sortie: object) -> Tuple[int, Tuple[int, ...], int, dict]:
    if isinstance(sortie, dict):
        return (
            int(sortie.get("launch", -1)),
            tuple(int(customer) for customer in sortie.get("customers", [])),
            int(sortie.get("recovery", -1)),
            sortie,
        )
    launch, customer, recovery = sortie  # type: ignore[misc]
    return int(launch), (int(customer),), int(recovery), {}


def capture_structural_projection(state: "TVDState") -> StructuralProjection:
    """Capture only stable business structure; never calls RNG/objective/checker."""

    van_routes = tuple(
        VanRouteFact(
            van_id=str(van_id),
            warehouse_id=_optional_int(state.van_home.get(str(van_id))),
            nodes=tuple(int(node) for node in route),
        )
        for van_id, route in sorted(state.van_routes.items())
    )
    route_positions = []
    route_segments = []
    for route in van_routes:
        for position, node in enumerate(route.nodes):
            route_positions.append(
                RoutePositionFact(
                    van_id=route.van_id,
                    route_position=position,
                    node_id=node,
                    predecessor_node=route.nodes[position - 1] if position else None,
                    successor_node=(
                        route.nodes[position + 1]
                        if position + 1 < len(route.nodes)
                        else None
                    ),
                )
            )
        for position, (start, end) in enumerate(zip(route.nodes, route.nodes[1:])):
            route_segments.append(
                RouteSegmentFact(
                    segment_id=f"van:{route.van_id}:segment:{position}-{position + 1}",
                    van_id=route.van_id,
                    start_position=position,
                    end_position=position + 1,
                    start_node=start,
                    end_node=end,
                )
            )

    sortie_facts = []
    occurrence_counts: Dict[str, int] = {}
    for sortie in state.drone_sorties:
        launch, customers, recovery, raw = _sortie_values(sortie)
        base = (
            _optional_str(raw.get("drone_id")),
            customers,
            launch,
            recovery,
            _optional_str(raw.get("launch_van_id")),
            _optional_str(raw.get("recovery_van_id")),
            _optional_int(raw.get("launch_position")),
            _optional_int(raw.get("recovery_position")),
        )
        base_digest = _digest(base)[:24]
        occurrence = occurrence_counts.get(base_digest, 0)
        occurrence_counts[base_digest] = occurrence + 1
        sortie_facts.append(
            DroneSortieFact(
                sortie_id=f"sortie:{base_digest}:{occurrence}",
                source_occurrence=occurrence,
                drone_id=base[0],
                customer_ids=customers,
                launch_node=launch,
                recovery_node=recovery,
                launch_van_id=base[4],
                recovery_van_id=base[5],
                launch_position=base[6],
                recovery_position=base[7],
            )
        )

    launch_recovery = tuple(
        LaunchRecoveryFact(
            sortie_id=sortie.sortie_id,
            launch_link_id=f"{sortie.sortie_id}:launch",
            recovery_link_id=f"{sortie.sortie_id}:recovery",
            launch_node=sortie.launch_node,
            recovery_node=sortie.recovery_node,
            launch_van_id=sortie.launch_van_id,
            recovery_van_id=sortie.recovery_van_id,
            launch_position=sortie.launch_position,
            recovery_position=sortie.recovery_position,
        )
        for sortie in sortie_facts
    )
    carrier_transfers = tuple(
        CarrierTransferFact(
            transfer_id=f"{sortie.sortie_id}:carrier",
            sortie_id=sortie.sortie_id,
            drone_id=sortie.drone_id,
            launch_carrier_van_id=sortie.launch_van_id,
            recovery_carrier_van_id=sortie.recovery_van_id,
            transferred=(
                sortie.launch_van_id != sortie.recovery_van_id
                if sortie.launch_van_id is not None
                and sortie.recovery_van_id is not None
                else None
            ),
        )
        for sortie in sortie_facts
    )

    current_carrier = {
        str(drone_id): str(van_id)
        for drone_id, van_id in state.drone_initial_carrier.items()
    }
    warehouses = {int(node) for node in state.transshipment_nodes}
    for sortie in sortie_facts:
        if sortie.drone_id is None:
            continue
        current_carrier[sortie.drone_id] = (
            None
            if sortie.recovery_node in warehouses
            else sortie.recovery_van_id
        )
    carrier_relations = tuple(
        CarrierRelationFact(
            relation_id=f"carrier:{drone_id}",
            drone_id=str(drone_id),
            initial_carrier_van_id=_optional_str(initial),
            current_carrier_van_id=_optional_str(current_carrier.get(str(drone_id))),
        )
        for drone_id, initial in sorted(state.drone_initial_carrier.items())
    )
    coordination_edges = tuple(
        edge
        for sortie in sortie_facts
        for edge in (
            CoordinationEdgeFact(
                edge_id=f"{sortie.sortie_id}:van-drone-launch",
                edge_kind="van-drone-launch",
                source_entity_id=f"van:{sortie.launch_van_id}",
                target_entity_id=f"drone:{sortie.drone_id}",
            ),
            CoordinationEdgeFact(
                edge_id=f"{sortie.sortie_id}:van-drone-recovery",
                edge_kind="van-drone-recovery",
                source_entity_id=f"drone:{sortie.drone_id}",
                target_entity_id=f"van:{sortie.recovery_van_id}",
            ),
            CoordinationEdgeFact(
                edge_id=f"{sortie.sortie_id}:launch-recovery-order",
                edge_kind="launch-recovery-order",
                source_entity_id=f"node:{sortie.launch_node}",
                target_entity_id=f"node:{sortie.recovery_node}",
            ),
        )
    )

    customer_ids = set(int(customer) for customer in state.service_mode)
    customer_ids.update(int(customer) for customer in state.unassigned)
    customer_ids.update(int(customer) for customer in state.order_assignment)
    customer_ids.update(
        position.node_id
        for position in route_positions
        if position.node_id not in warehouses
    )
    customer_ids.update(
        customer for sortie in sortie_facts for customer in sortie.customer_ids
    )
    service_facts = []
    for customer in sorted(customer_ids):
        assignment = state.order_assignment.get(customer, {})
        service_facts.append(
            CustomerServiceFact(
                customer_id=customer,
                service_mode=_optional_str(state.service_mode.get(customer)),
                unassigned=customer in state.unassigned,
                van_route_positions=tuple(
                    (position.van_id, position.route_position)
                    for position in route_positions
                    if position.node_id == customer
                ),
                drone_sortie_ids=tuple(
                    sortie.sortie_id
                    for sortie in sortie_facts
                    if customer in sortie.customer_ids
                ),
                container_id=_optional_int(assignment.get("container_id")),
                assigned_transshipment=_optional_int(
                    assignment.get("assigned_transshipment")
                ),
            )
        )

    business_metadata = {
        "route_endpoints": state.metadata.get("route_endpoints", ()),
        "warehouse_ready_time": state.metadata.get("warehouse_ready_time", {}),
    }
    return StructuralProjection(
        schema_version=STRUCTURAL_CONTEXT_VERSION,
        port_node=int(state.port_node),
        truck_depot_node=int(state.truck_depot_node),
        transshipment_nodes=tuple(int(node) for node in state.transshipment_nodes),
        selected_transshipment=int(state.selected_transshipment),
        container_origin=int(state.container_origin),
        truck_route=tuple(int(node) for node in state.truck_route),
        tractor_routes=_freeze(state.tractor_routes),
        tractor_home=_freeze(state.tractor_home),
        trailer_home=_freeze(state.trailer_home),
        container_routes=_freeze(state.container_routes),
        van_routes=van_routes,
        route_position_facts=tuple(route_positions),
        route_segment_facts=tuple(route_segments),
        drone_sortie_facts=tuple(sortie_facts),
        launch_recovery_facts=launch_recovery,
        carrier_relation_facts=carrier_relations,
        carrier_transfer_facts=carrier_transfers,
        coordination_edge_facts=coordination_edges,
        customer_service_facts=tuple(service_facts),
        order_assignment=_freeze(state.order_assignment),
        container_assignment=_freeze(state.container_assignment),
        van_home=_freeze(state.van_home),
        drone_initial_carrier=_freeze(state.drone_initial_carrier),
        drone_home_warehouse=_freeze(state.drone_home_warehouse),
        service_mode=tuple(
            (int(customer), str(mode))
            for customer, mode in sorted(state.service_mode.items())
        ),
        unassigned=tuple(int(customer) for customer in state.unassigned),
        business_metadata=_freeze(business_metadata),
    )


def structural_business_fingerprint(projection: StructuralProjection) -> str:
    return _digest(projection)


def _route_mutation(before: VanRouteFact, after: VanRouteFact) -> RouteMutationFact:
    pre = before.nodes
    post = after.nodes
    prefix = 0
    while prefix < min(len(pre), len(post)) and pre[prefix] == post[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(pre) - prefix
        and suffix < len(post) - prefix
        and pre[len(pre) - 1 - suffix] == post[len(post) - 1 - suffix]
    ):
        suffix += 1
    pre_end = len(pre) - suffix
    post_end = len(post) - suffix
    return RouteMutationFact(
        van_id=before.van_id,
        pre_start_position=prefix,
        pre_end_position=pre_end,
        pre_nodes=pre[prefix:pre_end],
        post_start_position=prefix,
        post_end_position=post_end,
        post_nodes=post[prefix:post_end],
        predecessor_boundary_node=pre[prefix - 1] if prefix else None,
        successor_boundary_node=pre[pre_end] if pre_end < len(pre) else None,
    )


def diff_structural_projection(
    pre: StructuralProjection,
    post: StructuralProjection,
    actually_unassigned_customer_ids: Iterable[int],
) -> Tuple[MutationFootprint, ExternalBoundaryEntities]:
    actual = {int(customer) for customer in actually_unassigned_customer_ids}
    pre_routes = {route.van_id: route for route in pre.van_routes}
    post_routes = {route.van_id: route for route in post.van_routes}
    route_mutations = []
    for van_id in sorted(set(pre_routes) | set(post_routes)):
        before = pre_routes.get(van_id, VanRouteFact(van_id, None, ()))
        after = post_routes.get(van_id, VanRouteFact(van_id, None, ()))
        if before.nodes != after.nodes:
            route_mutations.append(_route_mutation(before, after))

    pre_sorties = {sortie.sortie_id: sortie for sortie in pre.drone_sortie_facts}
    post_sorties = {sortie.sortie_id: sortie for sortie in post.drone_sortie_facts}
    removed_sorties = tuple(sorted(set(pre_sorties) - set(post_sorties)))
    added_sorties = tuple(sorted(set(post_sorties) - set(pre_sorties)))
    sortie_sequence_mutations = tuple(
        [
            SortieSequenceMutation(sortie_id, pre_sorties[sortie_id].customer_ids, ())
            for sortie_id in removed_sorties
        ]
        + [
            SortieSequenceMutation(sortie_id, (), post_sorties[sortie_id].customer_ids)
            for sortie_id in added_sorties
        ]
    )

    pre_service = {fact.customer_id: fact for fact in pre.customer_service_facts}
    post_service = {fact.customer_id: fact for fact in post.customer_service_facts}
    service_transitions = []
    unassigned_transitions = []
    for customer in sorted(set(pre_service) | set(post_service)):
        before = pre_service.get(customer)
        after = post_service.get(customer)
        transition = ServiceTransitionFact(
            customer_id=customer,
            pre_service_mode=before.service_mode if before else None,
            post_service_mode=after.service_mode if after else None,
            pre_unassigned=before.unassigned if before else False,
            post_unassigned=after.unassigned if after else False,
        )
        if transition.pre_service_mode != transition.post_service_mode:
            service_transitions.append(transition)
        if transition.pre_unassigned != transition.post_unassigned:
            unassigned_transitions.append(transition)

    pre_links = {
        item
        for fact in pre.launch_recovery_facts
        for item in (fact.launch_link_id, fact.recovery_link_id)
    }
    post_links = {
        item
        for fact in post.launch_recovery_facts
        for item in (fact.launch_link_id, fact.recovery_link_id)
    }
    pre_carriers = {fact.relation_id: fact for fact in pre.carrier_relation_facts}
    post_carriers = {fact.relation_id: fact for fact in post.carrier_relation_facts}
    mutated_carriers = {
        relation_id
        for relation_id in set(pre_carriers) | set(post_carriers)
        if pre_carriers.get(relation_id) != post_carriers.get(relation_id)
    }
    pre_transfers = {fact.transfer_id for fact in pre.carrier_transfer_facts}
    post_transfers = {fact.transfer_id for fact in post.carrier_transfer_facts}
    mutated_carriers.update(pre_transfers ^ post_transfers)
    pre_edges = {fact.edge_id for fact in pre.coordination_edge_facts}
    post_edges = {fact.edge_id for fact in post.coordination_edge_facts}

    known_customers = set(pre_service) | set(post_service)
    external_customers = set()
    external_resources = set()
    structural_entities = set()
    for mutation in route_mutations:
        external_resources.add(f"van:{mutation.van_id}")
        structural_entities.add(
            f"van:{mutation.van_id}:{mutation.pre_start_position}-{mutation.pre_end_position}"
        )
        for node in (
            mutation.predecessor_boundary_node,
            mutation.successor_boundary_node,
        ):
            if node in known_customers and node not in actual:
                external_customers.add(int(node))
    for sortie_id in removed_sorties:
        sortie = pre_sorties[sortie_id]
        structural_entities.add(sortie_id)
        if sortie.drone_id is not None:
            external_resources.add(f"drone:{sortie.drone_id}")
        for van_id in (sortie.launch_van_id, sortie.recovery_van_id):
            if van_id is not None:
                external_resources.add(f"van:{van_id}")
        for customer in (
            *sortie.customer_ids,
            sortie.launch_node,
            sortie.recovery_node,
        ):
            if customer in known_customers and customer not in actual:
                external_customers.add(customer)
    for transition in service_transitions:
        if transition.customer_id not in actual:
            external_customers.add(transition.customer_id)
    for customer in actual | external_customers:
        fact = pre_service.get(customer)
        if fact is None:
            continue
        if fact.container_id is not None:
            external_resources.add(f"container:{fact.container_id}")
        if fact.assigned_transshipment is not None:
            external_resources.add(f"warehouse:{fact.assigned_transshipment}")

    mutated_links = tuple(sorted(pre_links ^ post_links))
    mutated_edges = tuple(sorted(pre_edges ^ post_edges))
    structural_entities.update(mutated_links)
    structural_entities.update(mutated_edges)
    boundary = ExternalBoundaryEntities(
        customer_ids=tuple(sorted(external_customers)),
        resource_ids=tuple(sorted(external_resources)),
        structural_entity_ids=tuple(sorted(structural_entities)),
    )
    footprint = MutationFootprint(
        mutated_van_route_ids=tuple(mutation.van_id for mutation in route_mutations),
        mutated_contiguous_route_intervals=tuple(route_mutations),
        removed_or_replaced_sortie_ids=removed_sorties,
        added_or_replaced_sortie_ids=added_sorties,
        mutated_sortie_customer_sequences=sortie_sequence_mutations,
        mutated_launch_recovery_link_ids=mutated_links,
        mutated_carrier_relation_ids=tuple(sorted(mutated_carriers)),
        mutated_coordination_edge_ids=mutated_edges,
        service_mode_transitions=tuple(service_transitions),
        unassigned_transitions=tuple(unassigned_transitions),
        external_customers_touched=boundary.customer_ids,
        external_resources_touched=boundary.resource_ids,
    )
    return footprint, boundary


def producer_capabilities_for(source_destroy_operator: str) -> Tuple[str, ...]:
    descriptor = PRODUCER_DESCRIPTORS.get(source_destroy_operator)
    if descriptor is None:
        raise RemovalContextContractError(
            f"unregistered removal context producer: {source_destroy_operator}"
        )
    return descriptor.capabilities


def _context_id_payload(
    *,
    source_destroy_operator: str,
    pre_fingerprint: str,
    post_fingerprint: str,
    selected: Tuple[int, ...],
    actual: Tuple[int, ...],
    selection_order: Tuple[int, ...],
    deletion_order: Tuple[int, ...],
    actual_order: Tuple[int, ...],
) -> object:
    return {
        "schema_version": REMOVAL_CONTEXT_SCHEMA_VERSION,
        "structural_context_version": STRUCTURAL_CONTEXT_VERSION,
        "source_destroy_operator": source_destroy_operator,
        "pre_destroy_structural_fingerprint": pre_fingerprint,
        "post_destroy_structural_fingerprint": post_fingerprint,
        "selected_removed_customer_ids": selected,
        "actually_unassigned_customer_ids": actual,
        "customer_selection_order": selection_order,
        "deletion_attempt_order": deletion_order,
        "actual_unassignment_order": actual_order,
    }


def finalize_removal_structural_context(
    *,
    pre_projection: StructuralProjection,
    post_projection: StructuralProjection,
    source_destroy_operator: str,
    selected_removed_customer_ids: Iterable[int],
    customer_selection_order: Iterable[int],
    deletion_attempt_order: Iterable[int],
    actual_unassignment_order: Iterable[int],
    cascade_dependency_trace: Iterable[Tuple[int, int]] = (),
    cascade_native_partition_evidence: Iterable[Iterable[int]] = (),
    cascade_native_dependency_order: Iterable[Iterable[int]] = (),
) -> RemovalStructuralContext:
    capabilities = producer_capabilities_for(source_destroy_operator)
    selected = tuple(sorted({int(customer) for customer in selected_removed_customer_ids}))
    selection_order = tuple(int(customer) for customer in customer_selection_order)
    deletion_order = tuple(int(customer) for customer in deletion_attempt_order)
    actual_order = tuple(int(customer) for customer in actual_unassignment_order)
    actual = tuple(
        sorted(set(post_projection.unassigned) - set(pre_projection.unassigned))
    )
    if set(actual_order) != set(actual) or len(actual_order) != len(set(actual_order)):
        raise RemovalContextContractError(
            "actual unassignment order does not match authoritative pre/post transition"
        )
    if set(deletion_order) != set(selected):
        raise RemovalContextContractError(
            "deletion attempt order does not match selected removal set"
        )

    pre_fingerprint = structural_business_fingerprint(pre_projection)
    post_fingerprint = structural_business_fingerprint(post_projection)
    footprint, boundary = diff_structural_projection(pre_projection, post_projection, actual)
    context_id = _digest(
        _context_id_payload(
            source_destroy_operator=source_destroy_operator,
            pre_fingerprint=pre_fingerprint,
            post_fingerprint=post_fingerprint,
            selected=selected,
            actual=actual,
            selection_order=selection_order,
            deletion_order=deletion_order,
            actual_order=actual_order,
        )
    )
    relevant_customers = set(actual) | set(boundary.customer_ids)
    mutated_vans = set(footprint.mutated_van_route_ids)
    removed_sorties = set(footprint.removed_or_replaced_sortie_ids)
    customer_facts = tuple(
        fact
        for fact in pre_projection.customer_service_facts
        if fact.customer_id in relevant_customers
    )
    route_positions = tuple(
        fact
        for fact in pre_projection.route_position_facts
        if fact.node_id in relevant_customers and fact.van_id in mutated_vans
    )
    route_segments = tuple(
        fact
        for fact in pre_projection.route_segment_facts
        if fact.van_id in mutated_vans
        and ({fact.start_node, fact.end_node} & relevant_customers)
    )
    drone_sorties = tuple(
        fact
        for fact in pre_projection.drone_sortie_facts
        if fact.sortie_id in removed_sorties
    )
    launch_recovery = tuple(
        fact
        for fact in pre_projection.launch_recovery_facts
        if fact.sortie_id in removed_sorties
    )
    carrier_transfers = tuple(
        fact
        for fact in pre_projection.carrier_transfer_facts
        if fact.sortie_id in removed_sorties
    )
    coordination_edges = tuple(
        fact
        for fact in pre_projection.coordination_edge_facts
        if any(fact.edge_id.startswith(f"{sortie_id}:") for sortie_id in removed_sorties)
    )
    external_projection = tuple(
        fact
        for fact in pre_projection.customer_service_facts
        if fact.customer_id in boundary.customer_ids
    )
    context = RemovalStructuralContext(
        schema_version=REMOVAL_CONTEXT_SCHEMA_VERSION,
        structural_context_version=STRUCTURAL_CONTEXT_VERSION,
        context_id=context_id,
        source_destroy_operator=source_destroy_operator,
        producer_capabilities=capabilities,
        pre_destroy_structural_fingerprint=pre_fingerprint,
        post_destroy_structural_fingerprint=post_fingerprint,
        selected_removed_customer_ids=selected,
        actually_unassigned_customer_ids=actual,
        removal_order=deletion_order,
        customer_selection_order=selection_order,
        deletion_attempt_order=deletion_order,
        actual_unassignment_order=actual_order,
        pre_destroy_projection=pre_projection,
        post_destroy_projection=post_projection,
        customer_service_facts=customer_facts,
        route_position_facts=route_positions,
        route_segment_facts=route_segments,
        drone_sortie_facts=drone_sorties,
        launch_recovery_facts=launch_recovery,
        carrier_transfer_facts=carrier_transfers,
        coordination_edge_facts=coordination_edges,
        mutation_footprint=footprint,
        external_boundary_entities=boundary,
        external_boundary_projection=external_projection,
        cascade_dependency_trace=tuple(
            (int(source), int(dependency))
            for source, dependency in cascade_dependency_trace
        ),
        cascade_native_partition_evidence=tuple(
            tuple(int(customer) for customer in bundle)
            for bundle in cascade_native_partition_evidence
        ),
        cascade_native_dependency_order=tuple(
            tuple(int(customer) for customer in bundle)
            for bundle in cascade_native_dependency_order
        ),
    )
    validate_removal_structural_context(context)
    return context


def validate_removal_structural_context(context: RemovalStructuralContext) -> None:
    descriptor = PRODUCER_DESCRIPTORS.get(context.source_destroy_operator)
    if descriptor is None:
        raise RemovalContextContractError("context source is not a trusted producer")
    if context.schema_version not in descriptor.schema_versions:
        raise RemovalContextContractError("unsupported removal context schema")
    if context.structural_context_version != descriptor.structural_context_version:
        raise RemovalContextContractError("unsupported structural context version")
    if context.producer_capabilities != descriptor.capabilities:
        raise RemovalContextContractError("producer capability declaration mismatch")
    if structural_business_fingerprint(context.pre_destroy_projection) != (
        context.pre_destroy_structural_fingerprint
    ):
        raise RemovalContextContractError("pre projection fingerprint mismatch")
    if structural_business_fingerprint(context.post_destroy_projection) != (
        context.post_destroy_structural_fingerprint
    ):
        raise RemovalContextContractError("post projection fingerprint mismatch")
    actual = tuple(
        sorted(
            set(context.post_destroy_projection.unassigned)
            - set(context.pre_destroy_projection.unassigned)
        )
    )
    if actual != context.actually_unassigned_customer_ids:
        raise RemovalContextContractError("actual unassigned set mismatch")
    footprint, boundary = diff_structural_projection(
        context.pre_destroy_projection,
        context.post_destroy_projection,
        actual,
    )
    if footprint != context.mutation_footprint or boundary != context.external_boundary_entities:
        raise RemovalContextContractError("authoritative mutation diff mismatch")
    expected_id = _digest(
        _context_id_payload(
            source_destroy_operator=context.source_destroy_operator,
            pre_fingerprint=context.pre_destroy_structural_fingerprint,
            post_fingerprint=context.post_destroy_structural_fingerprint,
            selected=context.selected_removed_customer_ids,
            actual=context.actually_unassigned_customer_ids,
            selection_order=context.customer_selection_order,
            deletion_order=context.deletion_attempt_order,
            actual_order=context.actual_unassignment_order,
        )
    )
    if expected_id != context.context_id:
        raise RemovalContextContractError("context ID mismatch")


def active_removal_context(state: "TVDState") -> Optional[RemovalStructuralContext]:
    value = state.metadata.get(ACTIVE_REMOVAL_CONTEXT_KEY)
    if value is None:
        return None
    if not isinstance(value, RemovalStructuralContext):
        raise RemovalContextContractError("active removal context has an invalid type")
    return value


def attach_active_removal_context(
    state: "TVDState", context: RemovalStructuralContext
) -> "TVDState":
    if ACTIVE_REMOVAL_CONTEXT_KEY in state.metadata:
        raise RemovalContextLifecycleError("candidate already carries an active removal context")
    validate_removal_structural_context(context)
    state.metadata[ACTIVE_REMOVAL_CONTEXT_KEY] = context
    return state


def detach_active_removal_context(
    state: "TVDState",
) -> Optional[RemovalStructuralContext]:
    value = state.metadata.pop(ACTIVE_REMOVAL_CONTEXT_KEY, None)
    if value is None:
        return None
    if not isinstance(value, RemovalStructuralContext):
        raise RemovalContextContractError("active removal context has an invalid type")
    validate_removal_structural_context(value)
    return value


def discard_active_removal_context(state: "TVDState") -> bool:
    """Explicit safe discard for a new disposable destroy working copy."""

    return state.metadata.pop(ACTIVE_REMOVAL_CONTEXT_KEY, None) is not None


def assert_no_active_removal_context(state: "TVDState", *, owner: str) -> None:
    if ACTIVE_REMOVAL_CONTEXT_KEY in state.metadata:
        raise RemovalContextLifecycleError(
            f"persistent {owner} State carries an active removal structural context"
        )


def copy_metadata_with_immutable_context(metadata: Dict[str, object]) -> Dict[str, object]:
    context = metadata.get(ACTIVE_REMOVAL_CONTEXT_KEY)
    if context is not None and not isinstance(context, RemovalStructuralContext):
        raise RemovalContextContractError("active removal context has an invalid type")
    copied = copy.deepcopy(
        {key: value for key, value in metadata.items() if key != ACTIVE_REMOVAL_CONTEXT_KEY}
    )
    if context is not None:
        copied[ACTIVE_REMOVAL_CONTEXT_KEY] = context
    return copied


def removal_context_boundary(function: Callable) -> Callable:
    """Consume raw context at a public repair boundary and never return it."""

    @wraps(function)
    def wrapped(state: "TVDState", *args, **kwargs):
        detach_active_removal_context(state)
        try:
            result = function(state, *args, **kwargs)
        except BaseException:
            discard_active_removal_context(state)
            raise
        discard_active_removal_context(result)
        return result

    return wrapped
