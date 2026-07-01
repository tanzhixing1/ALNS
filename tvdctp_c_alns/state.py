from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


DroneSortie = Dict[str, object]


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

    def copy(self) -> "TVDState":
        return TVDState(
            port_node=self.port_node,
            truck_depot_node=self.truck_depot_node,
            transshipment_nodes=self.transshipment_nodes.copy(),
            selected_transshipment=self.selected_transshipment,
            container_origin=self.container_origin,
            truck_route=self.truck_route.copy(),
            van_route=self.van_route.copy(),
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
