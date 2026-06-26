from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CostConfig:
    """论文 Table 3 的深圳算例参数，toy 版先集中在这里维护。"""

    tractor_cost_per_km: float = 1.93
    van_cost_per_km: float = 0.875
    drone_cost_per_km: float = 0.052
    tractor_fixed_cost: float = 166.0
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
    num_trucks: int = 1
    num_vans: int = 1
    num_drones: int = 3
    drone_enabled: bool = True


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
    max_no_improvement: int = 100


@dataclass
class ToyDataConfig:
    port_node: int = 0
    truck_depot_node: int = 1
    transshipment_start_node: int = 2
    num_transshipments: int = 2
    num_customers: int = 6
    num_orders: int = 6
    num_containers: int = 1
    container_origin: str = "port"
    road_distance_factor: float = 1.18
    high_floor_ratio: float = 0.35
    min_demand_kg: int = 3
    max_demand_kg: int = 20
    service_time_min: float = 0.0
    time_window_start_min: float = 0.0
    time_window_end_min: float = 360.0


@dataclass
class TVDConfig:
    data: ToyDataConfig = field(default_factory=ToyDataConfig)
    fleet: FleetConfig = field(default_factory=FleetConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    alns: ALNSConfig = field(default_factory=ALNSConfig)
    output_dir: str = "outputs"


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
) -> TVDConfig:
    config = TVDConfig()
    config.data.num_customers = num_customers
    config.data.num_orders = num_orders
    config.data.num_transshipments = num_transshipments
    config.data.num_containers = num_containers
    config.data.container_origin = container_origin
    config.alns.max_iterations = iterations
    config.alns.random_seed = seed
    config.fleet.drone_enabled = drone_enabled
    config.output_dir = output_dir
    return config
