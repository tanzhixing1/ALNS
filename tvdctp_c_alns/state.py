from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

from alns_profile import add_value, increment


DroneSortie = Dict[str, object]


@dataclass(frozen=True)
class VanRoutePositionSnapshot:
    van_id: str
    route_position: int
    warehouse_id: Optional[int]


@dataclass(frozen=True)
class CustomerServiceSnapshot:
    customer_id: int
    service_mode: Optional[str]
    van_route_positions: Tuple[VanRoutePositionSnapshot, ...]
    container_id: Optional[int]
    assigned_transshipment: Optional[int]


@dataclass(frozen=True)
class VanRouteSegmentSnapshot:
    van_id: str
    warehouse_id: Optional[int]
    start_position: int
    end_position: int
    route_nodes: Tuple[int, ...]
    affected_positions: Tuple[int, ...]


@dataclass(frozen=True)
class DroneSubrouteSnapshot:
    sortie_id: str
    source_sortie_index: int
    drone_id: Optional[str]
    customer_ids: Tuple[int, ...]
    launch_node: int
    recovery_node: int


@dataclass(frozen=True)
class LaunchRecoverySnapshot:
    sortie_id: str
    launch_van_id: Optional[str]
    recovery_van_id: Optional[str]
    launch_node: int
    recovery_node: int
    launch_position: Optional[int]
    recovery_position: Optional[int]
    same_van_recovery: Optional[bool]


@dataclass(frozen=True)
class CarrierTransferSnapshot:
    sortie_id: str
    drone_id: Optional[str]
    initial_carrier_van_id: Optional[str]
    launch_carrier_van_id: Optional[str]
    recovery_carrier_van_id: Optional[str]
    carrier_transfer: Optional[bool]


@dataclass(frozen=True)
class ContainerDecisionSnapshot:
    container_id: int
    origin_node: Optional[int]
    destination_warehouse: Optional[int]
    tractor_id: Optional[str]
    trailer_id: Optional[str]
    unload_complete: Optional[float]


@dataclass(frozen=True)
class TruckWarehouseContextSnapshot:
    selected_transshipment: int
    container_decisions: Tuple[ContainerDecisionSnapshot, ...]


@dataclass(frozen=True)
class AffectedStructureScope:
    truck_context_ids: Tuple[str, ...]
    van_route_segment_ids: Tuple[str, ...]
    drone_subroute_ids: Tuple[str, ...]
    launch_recovery_link_ids: Tuple[str, ...]
    carrier_link_ids: Tuple[str, ...]
    coordination_edge_ids: Tuple[str, ...]


@dataclass(frozen=True)
class CascadeBundleSnapshot:
    """Immutable destroy-to-repair input for one Cascade customer bundle.

    ``dependency_order`` preserves only the order already produced by the
    current removal implementation.  The paper does not prescribe this order.
    Iteration is retained solely for compatibility with the pre-Stage-2D.1
    ``cascade_repair`` reader; this class does not implement repair semantics.
    """

    schema_version: int
    bundle_id: str
    source_operator: str
    source_destroy_call_id: str
    source_state_fingerprint: str
    customer_ids: Tuple[int, ...]
    dependency_order: Tuple[int, ...]
    dependency_order_semantics: str
    customer_service_snapshots: Tuple[CustomerServiceSnapshot, ...]
    affected_route_segments: Tuple[VanRouteSegmentSnapshot, ...]
    removed_drone_subroutes: Tuple[DroneSubrouteSnapshot, ...]
    launch_recovery_snapshots: Tuple[LaunchRecoverySnapshot, ...]
    carrier_transfer_snapshots: Tuple[CarrierTransferSnapshot, ...]
    truck_warehouse_context: TruckWarehouseContextSnapshot
    affected_structure_scope: AffectedStructureScope
    captured_before_removal: bool = True

    def __iter__(self) -> Iterator[int]:
        return iter(self.customer_ids)

    def __len__(self) -> int:
        return len(self.customer_ids)

    def canonical_json(self) -> str:
        return json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def contract_fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def default_timing() -> Dict[str, object]:
    return {
        "truck_arrival": {},
        "van_arrival": {},
        "drone_arrival": {},
        "service_start": {},
        "service_finish": {},
        "van_waiting_time": 0.0,
        "drone_waiting_time": 0.0,
        "early_waiting_time": 0.0,
        "time_window_violations": [],
        "van_arrival_by_van": {},
        "van_arrival_sequence_by_van": {},
    }


@dataclass
class TVDState:
    """Toy two-stage TVDCTP-T solution.

    The stage-1 truck route is fixed in this version. ALNS mainly changes
    the stage-2 van route and drone sorties.
    """

    port_node: int
    truck_depot_node: int
    transshipment_nodes: List[int]
    selected_transshipment: int
    container_origin: int
    truck_route: List[int]
    van_route: List[int]
    tractor_routes: Dict[str, List[Dict[str, object]]] = field(default_factory=dict)
    tractor_home: Dict[str, int] = field(default_factory=dict)
    trailer_home: Dict[str, int] = field(default_factory=dict)
    container_routes: Dict[int, Dict[str, object]] = field(default_factory=dict)
    van_routes: Dict[str, List[int]] = field(default_factory=dict)
    van_home: Dict[str, int] = field(default_factory=dict)
    drone_initial_carrier: Dict[str, str] = field(default_factory=dict)
    drone_home_warehouse: Dict[str, int] = field(default_factory=dict)
    drone_sorties: List[DroneSortie] = field(default_factory=list)
    order_assignment: Dict[int, Dict[str, object]] = field(default_factory=dict)
    container_assignment: Dict[int, Dict[str, object]] = field(default_factory=dict)
    service_mode: Dict[int, str] = field(default_factory=dict)
    unassigned: List[int] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)
    timing: Dict[str, object] = field(default_factory=default_timing)

    def __post_init__(self) -> None:
        if not self.van_routes and self.van_route:
            self.van_routes = {"van_0": self.van_route.copy()}
        if not self.van_route and self.van_routes:
            first_van = sorted(self.van_routes)[0]
            self.van_route = self.van_routes[first_van].copy()
        self.sync_primary_van_route()

    def sync_primary_van_route(self) -> None:
        if self.van_routes:
            non_empty = [
                van_id for van_id, route in sorted(self.van_routes.items())
                if len(route) >= 2
            ]
            first_van = non_empty[0] if non_empty else sorted(self.van_routes)[0]
            self.van_route = self.van_routes[first_van].copy()

    def route_for_van(self, van_id: str) -> List[int]:
        return self.van_routes.setdefault(str(van_id), [])

    def cache_signature(self) -> Tuple[object, ...]:
        start = time.perf_counter()
        def _sortie_signature(sortie: DroneSortie) -> Tuple[object, ...]:
            if isinstance(sortie, dict):
                return (
                    int(sortie.get("launch", -1)),
                    tuple(int(customer) for customer in sortie.get("customers", [])),
                    int(sortie.get("recovery", -1)),
                    str(sortie.get("drone_id", "")),
                    str(sortie.get("launch_van_id", "")),
                    str(sortie.get("recovery_van_id", "")),
                    int(sortie.get("launch_position", -1)),
                    int(sortie.get("recovery_position", -1)),
                )
            return tuple(sortie)  # type: ignore[arg-type]

        container_signature = tuple(
            (
                int(container_id),
                int(route.get("origin", -1)),
                int(route.get("destination_warehouse", -1)),
                float(route.get("unload_complete", 0.0)),
                tuple(int(customer) for customer in route.get("customers", [])),
            )
            for container_id, route in sorted(self.container_routes.items())
        )
        tractor_signature = tuple(
            (
                str(tractor_id),
                tuple(
                    (
                        str(event.get("event", "")),
                        int(event.get("node", -1)),
                        str(event.get("trailer_id", "")),
                        int(event.get("container_id", -1)),
                        round(float(event.get("arrival_time", 0.0)), 9),
                        round(float(event.get("departure_time", 0.0)), 9),
                    )
                    for event in route
                ),
            )
            for tractor_id, route in sorted(self.tractor_routes.items())
        )
        warehouse_ready_time = self.metadata.get("warehouse_ready_time", {})
        if isinstance(warehouse_ready_time, dict):
            warehouse_ready_signature = tuple(
                (int(warehouse), round(float(ready_time), 9))
                for warehouse, ready_time in sorted(warehouse_ready_time.items())
            )
        else:
            warehouse_ready_signature = ()
        order_assignment_signature = tuple(
            (
                int(customer),
                int(assignment.get("container_id", -1)),
                int(assignment.get("assigned_transshipment", -1)),
            )
            for customer, assignment in sorted(self.order_assignment.items())
        )
        container_assignment_signature = tuple(
            (
                int(container_id),
                int(assignment.get("destination_warehouse", -1)),
                int(assignment.get("selected_transshipment", -1)),
                tuple(int(customer) for customer in assignment.get("customers", [])),
            )
            for container_id, assignment in sorted(self.container_assignment.items())
        )
        signature = (
            int(self.selected_transshipment),
            int(self.container_origin),
            tuple(int(node) for node in self.truck_route),
            tuple((str(van_id), tuple(int(node) for node in route)) for van_id, route in sorted(self.van_routes.items())),
            tuple(_sortie_signature(sortie) for sortie in self.drone_sorties),
            tuple((int(customer), str(mode)) for customer, mode in sorted(self.service_mode.items())),
            tuple(int(customer) for customer in self.unassigned),
            tuple((str(van_id), int(home)) for van_id, home in sorted(self.van_home.items())),
            tuple((str(drone_id), str(van_id)) for drone_id, van_id in sorted(self.drone_initial_carrier.items())),
            container_signature,
            order_assignment_signature,
            container_assignment_signature,
            tractor_signature,
            warehouse_ready_signature,
        )
        increment("state_signature_calls")
        add_value("state_signature_time_total", time.perf_counter() - start)
        return signature

    def copy(self) -> "TVDState":
        increment("state_copy_calls")
        increment("state_deepcopy_calls", 7)
        return TVDState(
            port_node=self.port_node,
            truck_depot_node=self.truck_depot_node,
            transshipment_nodes=self.transshipment_nodes.copy(),
            selected_transshipment=self.selected_transshipment,
            container_origin=self.container_origin,
            truck_route=self.truck_route.copy(),
            van_route=self.van_route.copy(),
            tractor_routes=copy.deepcopy(self.tractor_routes),
            tractor_home=self.tractor_home.copy(),
            trailer_home=self.trailer_home.copy(),
            container_routes=copy.deepcopy(self.container_routes),
            van_routes=copy.deepcopy(self.van_routes),
            van_home=self.van_home.copy(),
            drone_initial_carrier=self.drone_initial_carrier.copy(),
            drone_home_warehouse=self.drone_home_warehouse.copy(),
            drone_sorties=copy.deepcopy(self.drone_sorties),
            order_assignment=copy.deepcopy(self.order_assignment),
            container_assignment=copy.deepcopy(self.container_assignment),
            service_mode=self.service_mode.copy(),
            unassigned=self.unassigned.copy(),
            metadata=copy.deepcopy(self.metadata),
            timing=copy.deepcopy(self.timing),
        )

    def objective(self, data=None, config=None):
        from objective import objective

        if data is None or config is None:
            raise ValueError("TVDState.objective() needs data and config in this project.")
        return objective(self, data, config)[0]

    @property
    def cost(self):
        cached = self.metadata.get("total_cost")
        if cached is None:
            raise ValueError("cost is not cached. Call objective(state, data, config) first.")
        return float(cached)

    def pretty_print(self) -> str:
        lines = [
            f"truck_route={self.truck_route}",
            f"tractor_routes={self.tractor_routes}",
            f"container_routes={self.container_routes}",
            f"van_route={self.van_route}",
            f"van_routes={self.van_routes}",
            f"drone_sorties={self.drone_sorties}",
            f"selected_transshipment={self.selected_transshipment}",
            f"container_origin={self.container_origin}",
            f"orders={len(self.order_assignment)}",
            f"containers={len(self.container_assignment)}",
            f"van_home={self.van_home}",
            f"drone_initial_carrier={self.drone_initial_carrier}",
            f"van_customers={self.get_van_customers()}",
            f"drone_customers={self.get_drone_customers()}",
            f"unassigned={self.unassigned}",
        ]
        return "\n".join(lines)

    def get_served_customers(self) -> List[int]:
        served = self.get_van_customers() + self.get_drone_customers()
        return sorted(set(served))

    def get_drone_customers(self) -> List[int]:
        customers = []
        for sortie in self.drone_sorties:
            if isinstance(sortie, dict):
                customers.extend(int(customer) for customer in sortie.get("customers", []))
            else:
                _, customer, _ = sortie
                customers.append(int(customer))
        return customers

    def get_van_customers(self) -> List[int]:
        endpoints = set(self.metadata.get("route_endpoints", [])) | set(self.transshipment_nodes)
        customers: List[int] = []
        routes = self.van_routes if self.van_routes else {"van_0": self.van_route}
        for route in routes.values():
            customers.extend(int(node) for node in route if node not in endpoints)
        return customers

    def mark_unassigned(self, customer: int) -> None:
        if customer not in self.unassigned:
            self.unassigned.append(customer)
        self.service_mode[customer] = "unassigned"

    def clean_unassigned(self, customer: int) -> None:
        self.unassigned = [item for item in self.unassigned if item != customer]
