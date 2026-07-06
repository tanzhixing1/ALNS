from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CostConfig:
    """论文 Table 3 的深圳算例参数，toy 版先集中在这里维护。"""

    tractor_cost_per_km: float = 1.93
    van_cost_per_km: float = 0.875
    drone_cost_per_km: float = 0.052
    tractor_fixed_cost: float = 166.0
    trailer_fixed_cost: float = 0.0
    van_fixed_cost: float = 59.0
    drone_fixed_cost: float = 169.0
    time_penalty_per_hour: float = 38.9
    infeasible_penalty: float = 10_000.0


@dataclass
class FleetConfig:
    # Distances are kilometers, speeds are kilometers/hour, and all timing
    # propagation in feasibility.py is reported in minutes.
    tractor_speed_kmph: float = 30.0
    van_speed_kmph: float = 40.0
    drone_speed_kmph: float = 80.0
    van_capacity_kg: float = 500.0
    drone_capacity_kg: float = 30.0
    drone_endurance_km: float = 90.0
    drone_battery_capacity_kwh: float = 13.8
    drone_payload_energy_coeff: float = 0.5
    drone_base_energy_coeff: float = 0.18
    drone_self_weight_kg: float = 5.0
    num_trucks: int = 1
    num_tractors: int = 1
    num_trailers: int = 1
    drones_per_van: int = 2
    drone_enabled: bool = True
    trailer_attach_time: float = 0.0
    trailer_detach_time: float = 0.0
    container_load_time: float = 0.0
    container_unload_time: float = 0.0


@dataclass
class ALNSConfig:
    max_iterations: int = 300
    random_seed: int = 42
    customer_removal_ratio: float = 0.2
    initial_temperature: float = 1000.0
    cooling_rate: float = 0.9995
    weight_update_interval: int = 50
    reaction_coefficient: float = 0.2
    scores: tuple[float, float, float, float] = (5.0, 3.0, 1.0, 0.0)
    max_no_improve: Optional[int] = 100
    max_no_improvement: Optional[int] = 100
    early_stop_enabled: bool = True
    enable_local_feasibility_cache: bool = False
    collect_local_feasibility_cache_stats: bool = False
    enable_shadow_prefilter: bool = False


@dataclass
class ToyDataConfig:
    port_node: int = 0
    truck_depot_node: int = 1
    tractor_depot_node: Optional[int] = None
    trailer_depot_node: Optional[int] = None
    transshipment_start_node: int = 3
    num_transshipments: int = 2
    num_customers: int = 6
    num_orders: int = 6
    num_containers: int = 1
    container_origin: str = "port"
    road_distance_factor: float = 1.0
    high_floor_ratio: float = 0.35
    min_demand_kg: int = 0
    max_demand_kg: int = 20
    min_pickup_demand_kg: int = 0
    max_pickup_demand_kg: int = 20
    service_time_min: float = 0.0
    time_window_start_min: float = 0.0
    time_window_end_min: float = 360.0
    vans_per_transshipment_by_scale: Dict[str, int] = field(
        default_factory=lambda: {"small": 2, "medium": 3, "large": 4}
    )
    warehouse_num_vans: Dict[int, int] = field(default_factory=dict)


@dataclass
class TVDConfig:
    data: ToyDataConfig = field(default_factory=ToyDataConfig)
    fleet: FleetConfig = field(default_factory=FleetConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    alns: ALNSConfig = field(default_factory=ALNSConfig)
    output_dir: str = "outputs"

    def transshipment_nodes(self) -> List[int]:
        start = self.data.transshipment_start_node
        return list(range(start, start + self.data.num_transshipments))

    def instance_scale(self) -> str:
        if self.data.num_customers <= 10:
            return "small"
        if self.data.num_customers <= 50:
            return "medium"
        return "large"

    def warehouse_num_vans(self, transshipment_nodes: Optional[List[int]] = None) -> Dict[int, int]:
        nodes = transshipment_nodes if transshipment_nodes is not None else self.transshipment_nodes()
        explicit = {int(node): int(count) for node, count in self.data.warehouse_num_vans.items()}
        if explicit:
            return {int(node): int(explicit.get(int(node), 0)) for node in nodes}

        vans = int(self.data.vans_per_transshipment_by_scale[self.instance_scale()])
        return {int(node): vans for node in nodes}

    def warehouse_num_drones(self, transshipment_nodes: Optional[List[int]] = None) -> Dict[int, int]:
        return {
            warehouse: vans * int(self.fleet.drones_per_van)
            for warehouse, vans in self.warehouse_num_vans(transshipment_nodes).items()
        }

    def total_num_vans(self, transshipment_nodes: Optional[List[int]] = None) -> int:
        return int(sum(self.warehouse_num_vans(transshipment_nodes).values()))

    def total_num_drones(self, transshipment_nodes: Optional[List[int]] = None) -> int:
        return int(sum(self.warehouse_num_drones(transshipment_nodes).values()))

    def build_van_home(self, transshipment_nodes: Optional[List[int]] = None) -> Dict[str, int]:
        van_home: Dict[str, int] = {}
        van_idx = 0
        for warehouse in sorted(self.warehouse_num_vans(transshipment_nodes)):
            for _ in range(self.warehouse_num_vans(transshipment_nodes)[warehouse]):
                van_home[f"van_{van_idx}"] = int(warehouse)
                van_idx += 1
        return van_home

    def build_drone_initial_carrier(
        self, transshipment_nodes: Optional[List[int]] = None
    ) -> Dict[str, str]:
        drone_initial_carrier: Dict[str, str] = {}
        drone_idx = 0
        for van_id in sorted(self.build_van_home(transshipment_nodes), key=lambda item: int(item.split("_")[1])):
            for _ in range(int(self.fleet.drones_per_van)):
                drone_initial_carrier[f"drone_{drone_idx}"] = van_id
                drone_idx += 1
        return drone_initial_carrier

    def build_drone_home_warehouse(
        self, transshipment_nodes: Optional[List[int]] = None
    ) -> Dict[str, int]:
        van_home = self.build_van_home(transshipment_nodes)
        return {
            drone_id: int(van_home[van_id])
            for drone_id, van_id in self.build_drone_initial_carrier(transshipment_nodes).items()
        }

    def build_tractor_home(self) -> Dict[str, int]:
        depot = (
            int(self.data.tractor_depot_node)
            if self.data.tractor_depot_node is not None
            else int(self.data.truck_depot_node)
        )
        return {
            f"tractor_{idx}": depot
            for idx in range(int(self.fleet.num_tractors))
        }

    def build_trailer_home(self, trailer_depot_node: Optional[int] = None) -> Dict[str, int]:
        depot = (
            int(trailer_depot_node)
            if trailer_depot_node is not None
            else int(self.data.trailer_depot_node)
            if self.data.trailer_depot_node is not None
            else int(self.data.transshipment_start_node - 1)
        )
        return {
            f"trailer_{idx}": depot
            for idx in range(int(self.fleet.num_trailers))
        }

    @property
    def num_vans(self) -> int:
        return self.total_num_vans()

    @property
    def num_drones(self) -> int:
        return self.total_num_drones()


def build_config(
    num_customers: int = 6,
    num_orders: int = 6,
    num_transshipments: int = 2,
    num_containers: int = 1,
    container_origin: str = "port",
    iterations: int = 300,
    seed: int = 42,
    drone_enabled: bool = True,
    output_dir: str = "outputs",
    drones_per_van: int = 2,
    num_tractors: int = 1,
    num_trailers: int = 1,
    warehouse_num_vans: Optional[Dict[int, int]] = None,
    max_no_improve: Optional[int] = 100,
    early_stop_enabled: bool = True,
    enable_local_feasibility_cache: bool = False,
) -> TVDConfig:
    config = TVDConfig()
    config.data.num_customers = num_customers
    config.data.num_orders = num_orders
    config.data.num_transshipments = num_transshipments
    config.data.num_containers = num_containers
    config.data.container_origin = container_origin
    config.alns.max_iterations = iterations
    config.alns.random_seed = seed
    config.alns.max_no_improve = max_no_improve
    config.alns.max_no_improvement = max_no_improve
    config.alns.early_stop_enabled = bool(early_stop_enabled)
    config.alns.enable_local_feasibility_cache = bool(enable_local_feasibility_cache)
    config.fleet.drone_enabled = drone_enabled
    config.fleet.drones_per_van = int(drones_per_van)
    config.fleet.num_tractors = int(num_tractors)
    config.fleet.num_trailers = int(num_trailers)
    config.fleet.num_trucks = int(num_tractors)
    if warehouse_num_vans is not None:
        config.data.warehouse_num_vans = {
            int(warehouse): int(count)
            for warehouse, count in warehouse_num_vans.items()
        }
    config.output_dir = output_dir
    return config
