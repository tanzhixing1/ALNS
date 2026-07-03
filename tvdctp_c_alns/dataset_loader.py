from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Dict, List, Tuple

import numpy as np

from config import TVDConfig


Coord = Tuple[float, float]


@dataclass
class InstanceData:
    port_node: int
    truck_depot_node: int
    tractor_depot_node: int
    trailer_depot_node: int
    transshipment_nodes: List[int]
    container_origin: int
    container_origin_type: str
    customers: List[int]
    nodes: List[int]
    coordinates: Dict[int, Coord]
    demands: Dict[int, float]
    pickup_demands: Dict[int, float]
    time_windows: Dict[int, Tuple[float, float]]
    service_times: Dict[int, float]
    is_high_floor: Dict[int, bool]
    drone_eligible: Dict[int, bool]
    orders: List[Dict[str, object]]
    container_data: Dict[int, Dict[str, object]]
    container_assignment: Dict[int, Dict[str, object]]
    ground_distance_matrix: np.ndarray
    drone_distance_matrix: np.ndarray

    @property
    def depot(self) -> int:
        """Backward-compatible alias: in this toy project, depot means port."""

        return self.port_node

    @property
    def transshipment(self) -> int:
        """Backward-compatible alias for the first candidate transshipment node."""

        return self.transshipment_nodes[0]

    @property
    def transshipment_node(self) -> int:
        """Backward-compatible alias for the first candidate transshipment node."""

        return self.transshipment_nodes[0]


def _euclidean(a: Coord, b: Coord) -> float:
    return float(hypot(a[0] - b[0], a[1] - b[1]))


def _build_distance_matrix(nodes: List[int], coords: Dict[int, Coord], factor: float) -> np.ndarray:
    size = max(nodes) + 1
    matrix = np.zeros((size, size), dtype=float)
    for i in nodes:
        for j in nodes:
            matrix[i, j] = _euclidean(coords[i], coords[j]) * factor
    return matrix


def generate_toy_data(config: TVDConfig) -> InstanceData:
    """Generate a reproducible toy instance.

    Node 0 is the port, node 1 is the truck depot, nodes 2.. are candidate
    transshipment warehouses, and the remaining nodes are customers.
    """

    rng = np.random.default_rng(config.alns.random_seed)
    port_node = config.data.port_node
    truck_depot_node = config.data.truck_depot_node
    tractor_depot_node = (
        int(config.data.tractor_depot_node)
        if config.data.tractor_depot_node is not None
        else truck_depot_node
    )
    trailer_depot_node = (
        int(config.data.trailer_depot_node)
        if config.data.trailer_depot_node is not None
        else int(config.data.transshipment_start_node - 1)
    )
    transshipment_start_node = int(config.data.transshipment_start_node)
    if trailer_depot_node >= transshipment_start_node:
        transshipment_start_node = trailer_depot_node + 1
    transshipment_nodes = list(
        range(
            transshipment_start_node,
            transshipment_start_node + config.data.num_transshipments,
        )
    )
    customer_start = transshipment_start_node + config.data.num_transshipments
    customers = list(range(customer_start, customer_start + config.data.num_customers))
    truck_depot_node = tractor_depot_node
    nodes = (
        [port_node, tractor_depot_node, trailer_depot_node]
        + transshipment_nodes
        + customers
    )
    if len(set(nodes)) != len(nodes):
        raise ValueError(
            "Node ids must be unique across port, tractor depot, trailer depot, warehouses, and customers."
        )

    coordinates: Dict[int, Coord] = {
        port_node: (5.0, 5.0),
        truck_depot_node: (0.0, 12.0),
    }
    coordinates[tractor_depot_node] = coordinates.get(tractor_depot_node, (0.0, 12.0))
    coordinates[trailer_depot_node] = (8.0, 18.0)

    for idx, transshipment in enumerate(transshipment_nodes):
        coordinates[transshipment] = (
            28.0 + 20.0 * idx,
            24.0 - 6.0 * idx,
        )

    for customer in customers:
        coordinates[customer] = (
            float(rng.uniform(12.0, 55.0)),
            float(rng.uniform(8.0, 52.0)),
        )

    demands = {
        customer: float(
            rng.integers(config.data.min_demand_kg, config.data.max_demand_kg + 1)
        )
        for customer in customers
    }
    pickup_demands = {
        customer: float(
            rng.integers(
                config.data.min_pickup_demand_kg,
                config.data.max_pickup_demand_kg + 1,
            )
        )
        for customer in customers
    }

    service_times = {customer: config.data.service_time_min for customer in customers}
    time_windows = {
        customer: (
            config.data.time_window_start_min,
            config.data.time_window_end_min,
        )
        for customer in customers
    }

    high_count = (
        0
        if config.data.high_floor_ratio <= 0
        else max(1, round(len(customers) * config.data.high_floor_ratio))
    )
    high_floor_customers = set(rng.choice(customers, high_count, replace=False).tolist())

    is_high_floor: Dict[int, bool] = {}
    drone_eligible: Dict[int, bool] = {}
    for customer in customers:
        is_high_floor[customer] = customer in high_floor_customers
        drone_eligible[customer] = True

    origin_key = config.data.container_origin
    if origin_key == "port":
        container_origin = port_node
        container_origin_type = "port"
    elif origin_key.startswith("transshipment_"):
        origin_idx = int(origin_key.split("_", 1)[1])
        container_origin = transshipment_nodes[origin_idx]
        container_origin_type = "transshipment"
    else:
        container_origin = port_node
        container_origin_type = "port"

    num_containers = max(1, int(config.data.num_containers))
    orders = []
    order_count = min(config.data.num_orders, len(customers))
    for order_id, customer in enumerate(customers[:order_count]):
        container_id = int(order_id % num_containers)
        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer,
                "container_id": container_id,
                "origin_port": port_node,
                "container_origin": container_origin,
                "assigned_transshipment": None,
                "demand": demands[customer],
                "pickup_demand": pickup_demands[customer],
                "service_required": True,
            }
        )

    container_assignment: Dict[int, Dict[str, object]] = {}
    for container_id in range(num_containers):
        container_orders = [
            int(order["order_id"])
            for order in orders
            if int(order["container_id"]) == int(container_id)
        ]
        container_customers = [
            int(order["customer_id"])
            for order in orders
            if int(order["container_id"]) == int(container_id)
        ]
        container_assignment[container_id] = {
            "container_id": int(container_id),
            "origin_node": container_origin,
            "origin": container_origin,
            "origin_type": container_origin_type,
            "candidate_transshipments": transshipment_nodes.copy(),
            "selected_transshipment": None,
            "destination_warehouse": None,
            "assigned_orders": container_orders,
            "orders": container_orders,
            "customers": container_customers,
        }
    container_data = {
        int(container_id): dict(assignment)
        for container_id, assignment in container_assignment.items()
    }

    ground = _build_distance_matrix(
        nodes, coordinates, factor=config.data.road_distance_factor
    )
    drone = _build_distance_matrix(nodes, coordinates, factor=1.0)

    return InstanceData(
        port_node=port_node,
        truck_depot_node=truck_depot_node,
        tractor_depot_node=tractor_depot_node,
        trailer_depot_node=trailer_depot_node,
        transshipment_nodes=transshipment_nodes,
        container_origin=container_origin,
        container_origin_type=container_origin_type,
        customers=customers,
        nodes=nodes,
        coordinates=coordinates,
        demands=demands,
        pickup_demands=pickup_demands,
        time_windows=time_windows,
        service_times=service_times,
        is_high_floor=is_high_floor,
        drone_eligible=drone_eligible,
        orders=orders,
        container_data=container_data,
        container_assignment=container_assignment,
        ground_distance_matrix=ground,
        drone_distance_matrix=drone,
    )
