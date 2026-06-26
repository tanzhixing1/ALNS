from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw

from alns_solver import ALNSResult
from config import TVDConfig
from dataset_loader import InstanceData
from feasibility import (
    check_solution_feasible,
    compute_timing,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_energy_details,
    sortie_nodes,
    update_drone_sortie_timing,
)
from objective import objective
from state import TVDState


def _fmt(value: object, digits: int = 3) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _node_type(node: int, data: InstanceData) -> str:
    if node == data.port_node:
        return "port"
    if node == data.truck_depot_node:
        return "truck_depot"
    if node in data.transshipment_nodes:
        return "transshipment"
    if node in data.customers:
        return "customer"
    return "unknown"


def _travel_minutes(distance: float, speed_kmph: float) -> float:
    return float(distance) / speed_kmph * 60.0


def _van_sequence_lookup(timing: Dict[str, object]) -> Dict[int, Dict[str, float]]:
    lookup = {}
    for item in timing.get("van_arrival_sequence", []):
        if isinstance(item, dict):
            lookup[int(item["route_index"])] = {
                "node": float(item["node"]),
                "arrival_time": float(item["arrival_time"]),
            }
    return lookup


def _route_position(route: List[int], node: int, start: int = 0) -> int:
    for idx in range(start, len(route)):
        if route[idx] == node:
            return idx
    return -1


def _total_delivery_load(state: TVDState, data: InstanceData) -> float:
    served = set(state.get_van_customers() + state.get_drone_customers())
    return float(sum(data.demands[customer] for customer in served))


def _sorties_by_launch_position(state: TVDState) -> Dict[int, List[dict]]:
    launch_positions: Dict[int, List[dict]] = {}
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        launch, _, _ = sortie_nodes(sortie)
        launch_pos = int(sortie.get("launch_position", _route_position(state.van_route, launch)))
        if launch_pos >= 0:
            launch_positions.setdefault(launch_pos, []).append(sortie)
    return launch_positions


def _van_load_updates(state: TVDState, data: InstanceData) -> List[Dict[str, float]]:
    van_customers = set(state.get_van_customers())
    sorties_by_launch = _sorties_by_launch_position(state)
    remaining_load = _total_delivery_load(state, data)
    updates = []

    for route_index, node in enumerate(state.van_route):
        node = int(node)
        load_arrival = remaining_load
        delivered = float(data.demands[node]) if node in van_customers else 0.0
        load_after_service = load_arrival - delivered
        launched_payload = float(
            sum(
                data.demands[customer]
                for sortie in sorties_by_launch.get(route_index, [])
                for customer in sortie_nodes(sortie)[1]
            )
        )
        load_departure = load_after_service - launched_payload
        updates.append(
            {
                "route_index": float(route_index),
                "node": float(node),
                "load_arrival": float(load_arrival),
                "delivered": float(delivered),
                "launched_payload": float(launched_payload),
                "load_departure": float(load_departure),
            }
        )
        remaining_load = load_departure

    return updates


def _truck_load_updates(state: TVDState, data: InstanceData) -> List[Dict[str, float]]:
    container_payload = _total_delivery_load(state, data)
    remaining_containers = 0.0
    remaining_payload = 0.0
    updates = []

    for route_index, node in enumerate(state.truck_route):
        node = int(node)
        containers_arrival = remaining_containers
        payload_arrival = remaining_payload
        operation = ""
        if node == state.container_origin and node != state.selected_transshipment:
            remaining_containers = 1.0
            remaining_payload = container_payload
            operation = "load_container"
        if node == state.selected_transshipment and remaining_containers > 0:
            remaining_containers = 0.0
            remaining_payload = 0.0
            operation = "unload_container"
        updates.append(
            {
                "route_index": float(route_index),
                "node": float(node),
                "containers_arrival": float(containers_arrival),
                "payload_arrival": float(payload_arrival),
                "containers_departure": float(remaining_containers),
                "payload_departure": float(remaining_payload),
                "operation": operation,
            }
        )

    return updates


def _scale_points(data: InstanceData, width: int, height: int, pad: int) -> Dict[int, Tuple[int, int]]:
    xs = [coord[0] for coord in data.coordinates.values()]
    ys = [coord[1] for coord in data.coordinates.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(coord):
        x, y = coord
        sx = pad + (x - min_x) / max(max_x - min_x, 1e-9) * (width - 2 * pad)
        sy = height - pad - (y - min_y) / max(max_y - min_y, 1e-9) * (height - 2 * pad)
        return int(sx), int(sy)

    return {node: scale(coord) for node, coord in data.coordinates.items()}


def save_convergence_plot(history: List[Dict[str, object]], output_path: Path) -> None:
    width, height, pad = 900, 420, 50
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((pad, pad, width - pad, height - pad), outline=(220, 220, 220))

    if not history:
        img.save(output_path)
        return

    values = [float(row["best_cost"]) for row in history]
    min_v, max_v = min(values), max(values)
    span = max(max_v - min_v, 1e-9)
    points = []
    for idx, value in enumerate(values):
        x = pad + idx / max(len(values) - 1, 1) * (width - 2 * pad)
        y = height - pad - (value - min_v) / span * (height - 2 * pad)
        points.append((int(x), int(y)))

    if len(points) > 1:
        draw.line(points, fill=(35, 98, 185), width=3)
    for point in points[:: max(1, len(points) // 20)]:
        draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill=(35, 98, 185))

    draw.text((pad, 18), "Best objective convergence", fill=(30, 30, 30))
    draw.text((pad, height - pad + 14), "iteration", fill=(60, 60, 60))
    draw.text((pad + 5, pad + 5), f"max {max_v:.2f}", fill=(80, 80, 80))
    draw.text((pad + 5, height - pad - 18), f"min {min_v:.2f}", fill=(80, 80, 80))
    img.save(output_path)


def save_routes_plot(state: TVDState, data: InstanceData, output_path: Path) -> None:
    width, height, pad = 900, 650, 55
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    points = _scale_points(data, width, height, pad)

    truck_route = state.truck_route
    for idx in range(len(truck_route) - 1):
        draw.line((points[truck_route[idx]], points[truck_route[idx + 1]]), fill=(214, 39, 40), width=3)

    route = state.van_route
    for idx in range(len(route) - 1):
        draw.line((points[route[idx]], points[route[idx + 1]]), fill=(31, 119, 180), width=4)

    for sortie in state.drone_sorties:
        launch, customers, recovery = sortie_nodes(sortie)
        path = [launch] + customers + [recovery]
        for idx in range(len(path) - 1):
            draw.line((points[path[idx]], points[path[idx + 1]]), fill=(44, 160, 44), width=2)

    for node, point in points.items():
        if node == data.port_node:
            color = (214, 39, 40)
            radius = 9
            label = "Port 0"
        elif node == data.truck_depot_node:
            color = (121, 85, 72)
            radius = 9
            label = f"Truck depot {node}"
        elif node == state.selected_transshipment:
            color = (255, 127, 14)
            radius = 9
            label = f"Selected WH {node}"
        elif node in data.transshipment_nodes:
            color = (255, 193, 7)
            radius = 8
            label = f"Candidate WH {node}"
        elif data.is_high_floor.get(node, False):
            color = (148, 103, 189)
            radius = 7
            label = f"C{node} H"
        elif state.service_mode.get(node) == "drone":
            color = (44, 160, 44)
            radius = 7
            label = f"C{node} D"
        else:
            color = (31, 119, 180)
            radius = 7
            label = f"C{node} V"
        x, y = point
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=(30, 30, 30))
        draw.text((x + 10, y - 8), label, fill=(30, 30, 30))

    draw.text((pad, 20), "TVDCTP-T route: red=truck, blue=van, green=drone", fill=(30, 30, 30))
    img.save(output_path)


def _append_csv_row(
    rows: List[Dict[str, object]],
    section: str,
    row_type: str,
    item_id: object,
    field: str,
    value: object,
) -> None:
    rows.append(
        {
            "section": section,
            "row_type": row_type,
            "item_id": item_id,
            "field": field,
            "value": value,
        }
    )


def save_route_plan_detail(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    metrics: Dict[str, object],
    output_dir: Path,
) -> None:
    timing = state.timing
    feasible, violations = check_solution_feasible(state, data, config)
    timing = state.timing
    van_sequence = _van_sequence_lookup(timing)
    service_start = timing.get("service_start", {})
    service_finish = timing.get("service_finish", {})
    drone_arrival = timing.get("drone_arrival", {})
    truck_arrival = timing.get("truck_arrival", {})
    truck_load_updates = _truck_load_updates(state, data)
    van_load_updates = _van_load_updates(state, data)

    lines: List[str] = []
    csv_rows: List[Dict[str, object]] = []

    lines.append("TVDCTP-T Route Plan Detail")
    lines.append("=" * 80)
    lines.append("All times are minutes. Distances are kilometers.")
    lines.append("waiting_cost_reported is reported only and is not included in total_cost.")
    lines.append("")

    lines.append("0. Problem Settings and Parameters")
    settings = {
        "num_orders": config.data.num_orders,
        "num_customers": config.data.num_customers,
        "num_containers": config.data.num_containers,
        "num_transshipments": config.data.num_transshipments,
        "candidate_transshipment_nodes": data.transshipment_nodes,
        "owned_num_trucks": config.fleet.num_trucks,
        "owned_num_vans": config.fleet.num_vans,
        "owned_num_drones": config.fleet.num_drones,
        "used_trucks": metrics.get("used_trucks", 0),
        "used_vans": metrics.get("used_vans", 0),
        "used_drones": metrics.get("used_drones", 0),
        "used_drone_sorties": metrics.get("used_drone_sorties", 0),
        "distance_metric": "Euclidean distance",
        "ground_distance_factor": config.data.road_distance_factor,
        "tractor_speed_kmph": config.fleet.tractor_speed_kmph,
        "van_speed_kmph": config.fleet.van_speed_kmph,
        "drone_speed_kmph": config.fleet.drone_speed_kmph,
        "van_capacity_kg": config.fleet.van_capacity_kg,
        "drone_capacity_kg": config.fleet.drone_capacity_kg,
        "drone_endurance_km": config.fleet.drone_endurance_km,
        "drone_battery_capacity_kwh": config.fleet.drone_battery_capacity_kwh,
        "drone_payload_energy_coeff_rou": config.fleet.drone_payload_energy_coeff,
        "drone_base_energy_coeff_rou1": config.fleet.drone_base_energy_coeff,
        "drone_self_weight_kg": config.fleet.drone_self_weight_kg,
        "tractor_cost_per_km": config.cost.tractor_cost_per_km,
        "van_cost_per_km": config.cost.van_cost_per_km,
        "drone_cost_per_km": config.cost.drone_cost_per_km,
        "tractor_fixed_cost": config.cost.tractor_fixed_cost,
        "van_fixed_cost": config.cost.van_fixed_cost,
        "drone_fixed_cost": config.cost.drone_fixed_cost,
        "default_time_window": (
            config.data.time_window_start_min,
            config.data.time_window_end_min,
        ),
        "customer_service_time_min": config.data.service_time_min,
        "low_floor_service_rule": "low-floor customers can be served by van or drone; optimizer decides service_mode",
        "high_floor_service_rule": "high-floor customers must be served by drone",
        "drone_energy_formula": "energy += [rou * (pickup_load + delivery_load + drone_self_weight) + rou1] * flight_hours",
        "waiting_cost_in_objective": False,
        "used_drones_note": "physical drone count after assigning drone_id to sorties",
    }
    for field, value in settings.items():
        lines.append(f"{field}: {value}")
        _append_csv_row(csv_rows, "problem_settings", "setting", field, field, value)
    lines.append("")

    lines.append("一、节点与订单信息表")
    header = (
        "node_id | node_type | x | y | demand | time_window | service_time | "
        "drone_eligible | high_floor | order_id | container_id | assigned_transshipment"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for node in data.nodes:
        coord = data.coordinates[node]
        assignment = state.order_assignment.get(node, {})
        row = {
            "node_id": node,
            "node_type": _node_type(node, data),
            "x": coord[0],
            "y": coord[1],
            "demand": data.demands.get(node, ""),
            "time_window": data.time_windows.get(node, ""),
            "service_time": data.service_times.get(node, ""),
            "drone_eligible": data.drone_eligible.get(node, ""),
            "high_floor": data.is_high_floor.get(node, ""),
            "order_id": assignment.get("order_id", ""),
            "container_id": assignment.get("container_id", ""),
            "assigned_transshipment": assignment.get("assigned_transshipment", ""),
        }
        lines.append(
            f"{row['node_id']} | {row['node_type']} | {_fmt(row['x'])} | {_fmt(row['y'])} | "
            f"{row['demand']} | {row['time_window']} | {row['service_time']} | "
            f"{row['drone_eligible']} | {row['high_floor']} | {row['order_id']} | "
            f"{row['container_id']} | {row['assigned_transshipment']}"
        )
        for field, value in row.items():
            _append_csv_row(csv_rows, "nodes_orders", "node", node, field, value)
    lines.append("")

    lines.append("二、集装箱与一阶段 truck 运输")
    for container_id, assignment in state.container_assignment.items():
        lines.append(f"container_id: {container_id}")
        lines.append(f"container_origin: {assignment.get('origin_node')}")
        lines.append(f"selected_transshipment: {assignment.get('selected_transshipment')}")
        for field in ("origin_node", "selected_transshipment", "orders", "customers"):
            _append_csv_row(
                csv_rows,
                "container_truck",
                "container",
                container_id,
                field,
                assignment.get(field),
            )
    lines.append(f"truck_depot_node: {state.truck_depot_node}")
    lines.append(f"truck_route: {' -> '.join(str(node) for node in state.truck_route)}")
    lines.append("truck segments:")
    lines.append(
        "from | to | distance | travel_time | arrival_time | "
        "container_load_departure_from | payload_kg_departure_from | "
        "container_load_arrival_at_to | payload_kg_arrival_at_to | "
        "operation_at_to | container_load_departure_at_to | payload_kg_departure_at_to"
    )
    for idx in range(len(state.truck_route) - 1):
        start = state.truck_route[idx]
        end = state.truck_route[idx + 1]
        distance = float(data.ground_distance_matrix[start, end])
        travel_time = _travel_minutes(distance, config.fleet.tractor_speed_kmph)
        arrival_time = float(truck_arrival.get(end, 0.0))
        start_load = truck_load_updates[idx]
        end_load = truck_load_updates[idx + 1]
        lines.append(
            f"{start} | {end} | {_fmt(distance)} | {_fmt(travel_time)} | {_fmt(arrival_time)} | "
            f"{_fmt(start_load['containers_departure'])} | {_fmt(start_load['payload_departure'])} | "
            f"{_fmt(end_load['containers_arrival'])} | {_fmt(end_load['payload_arrival'])} | "
            f"{end_load['operation']} | {_fmt(end_load['containers_departure'])} | "
            f"{_fmt(end_load['payload_departure'])}"
        )
        for field, value in {
            "from": start,
            "to": end,
            "distance": distance,
            "travel_time": travel_time,
            "arrival_time": arrival_time,
            "container_load_departure_from": start_load["containers_departure"],
            "payload_kg_departure_from": start_load["payload_departure"],
            "container_load_arrival_at_to": end_load["containers_arrival"],
            "payload_kg_arrival_at_to": end_load["payload_arrival"],
            "operation_at_to": end_load["operation"],
            "container_load_departure_at_to": end_load["containers_departure"],
            "payload_kg_departure_at_to": end_load["payload_departure"],
        }.items():
            _append_csv_row(csv_rows, "container_truck", "truck_segment", idx + 1, field, value)
    lines.append(
        "truck_arrival_time at selected_transshipment: "
        f"{_fmt(timing.get('truck_arrival_time', 0.0))}"
    )
    lines.append("")

    lines.append("三、二阶段 van 路线")
    lines.append(f"van_route: {' -> '.join(str(node) for node in state.van_route)}")
    lines.append(
        "from | to | distance | travel_time | arrival_time_at_to | "
        "service_start | service_finish | time_window | time_window_ok | "
        "load_departure_from | load_arrival_at_to | delivered_at_to | "
        "launched_payload_at_to | load_departure_at_to"
    )
    for idx in range(len(state.van_route) - 1):
        start = state.van_route[idx]
        end = state.van_route[idx + 1]
        distance = float(data.ground_distance_matrix[start, end])
        travel_time = _travel_minutes(distance, config.fleet.van_speed_kmph)
        arrival_time = float(van_sequence.get(idx + 1, {}).get("arrival_time", 0.0))
        tw = data.time_windows.get(end, "")
        start_service = service_start.get(end, "")
        finish_service = service_finish.get(end, "")
        tw_ok = ""
        if end in data.customers and start_service != "":
            tw_ok = float(start_service) <= float(data.time_windows[end][1]) + 1e-9
        start_load = van_load_updates[idx]
        end_load = van_load_updates[idx + 1]
        lines.append(
            f"{start} | {end} | {_fmt(distance)} | {_fmt(travel_time)} | {_fmt(arrival_time)} | "
            f"{_fmt(start_service) if start_service != '' else ''} | "
            f"{_fmt(finish_service) if finish_service != '' else ''} | {tw} | {tw_ok} | "
            f"{_fmt(start_load['load_departure'])} | {_fmt(end_load['load_arrival'])} | "
            f"{_fmt(end_load['delivered'])} | {_fmt(end_load['launched_payload'])} | "
            f"{_fmt(end_load['load_departure'])}"
        )
        for field, value in {
            "from": start,
            "to": end,
            "distance": distance,
            "travel_time": travel_time,
            "arrival_time_at_to": arrival_time,
            "service_start": start_service,
            "service_finish": finish_service,
            "time_window": tw,
            "time_window_ok": tw_ok,
            "load_departure_from": start_load["load_departure"],
            "load_arrival_at_to": end_load["load_arrival"],
            "delivered_at_to": end_load["delivered"],
            "launched_payload_at_to": end_load["launched_payload"],
            "load_departure_at_to": end_load["load_departure"],
        }.items():
            _append_csv_row(csv_rows, "van_route", "van_segment", idx + 1, field, value)
    lines.append("")

    lines.append("van node load updates:")
    lines.append(
        "route_index | node | load_arrival | delivered_here | "
        "launched_payload_here | load_departure"
    )
    for update in van_load_updates:
        route_index = int(update["route_index"])
        node = int(update["node"])
        lines.append(
            f"{route_index} | {node} | {_fmt(update['load_arrival'])} | "
            f"{_fmt(update['delivered'])} | {_fmt(update['launched_payload'])} | "
            f"{_fmt(update['load_departure'])}"
        )
        for field, value in update.items():
            _append_csv_row(
                csv_rows,
                "van_route",
                "van_node_load",
                route_index,
                field,
                value,
            )
    lines.append("")

    lines.append("四、无人机 sorties")
    for sortie_idx, sortie in enumerate(state.drone_sorties, start=1):
        launch, customers, recovery = sortie_nodes(sortie)
        payload = float(sum(data.demands[customer] for customer in customers))
        distance = drone_sortie_distance(sortie, data)
        energy, energy_rows = drone_sortie_energy_details(sortie, data, config)
        flight_time = _travel_minutes(distance, config.fleet.drone_speed_kmph)
        launch_pos = int(sortie.get("launch_position", _route_position(state.van_route, launch))) if isinstance(sortie, dict) else _route_position(state.van_route, launch)
        recovery_pos = int(sortie.get("recovery_position", _route_position(state.van_route, recovery, launch_pos))) if isinstance(sortie, dict) else _route_position(state.van_route, recovery, launch_pos)
        van_arrival_recovery = float(
            van_sequence.get(recovery_pos, {}).get("arrival_time", 0.0)
        )
        delivery_load_departure = payload
        pickup_load_departure = 0.0
        effective_weight = (
            delivery_load_departure
            + pickup_load_departure
            + config.fleet.drone_self_weight_kg
        )
        sortie_fields = {
            "drone_id": int(sortie.get("drone_id", 0)) if isinstance(sortie, dict) else 0,
            "launch_node": launch,
            "launch_position": launch_pos,
            "launch_time": float(sortie.get("launch_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            "customers": customers,
            "recovery_node": recovery,
            "recovery_position": recovery_pos,
            "recovery_time": float(sortie.get("recovery_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            "same_node": launch == recovery,
            "delivery_load_departure": delivery_load_departure,
            "pickup_load_departure": pickup_load_departure,
            "effective_weight": effective_weight,
            "flight_hours": distance / config.fleet.drone_speed_kmph,
            "energy_increment_kwh": energy,
            "cumulative_energy_kwh": energy,
            "total_payload": payload,
            "total_drone_distance": distance,
            "total_drone_energy_kwh": energy,
            "drone_flight_time": flight_time,
            "van_arrival_recovery": van_arrival_recovery,
            "van_waiting_time": float(sortie.get("van_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            "drone_waiting_time": float(sortie.get("drone_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            "endurance_feasible": distance <= config.fleet.drone_endurance_km,
            "battery_feasible": energy <= config.fleet.drone_battery_capacity_kwh,
            "payload_feasible": payload <= config.fleet.drone_capacity_kg,
        }
        lines.append(f"Drone sortie {sortie_idx}:")
        for field, value in sortie_fields.items():
            lines.append(f"- {field}: {_fmt(value)}")
            _append_csv_row(csv_rows, "drone_sorties", "sortie", sortie_idx, field, value)
        drone_route = [launch] + customers + [recovery]
        lines.append(f"  drone_route: {' -> '.join(str(node) for node in drone_route)}")
        _append_csv_row(
            csv_rows,
            "drone_sorties",
            "sortie",
            sortie_idx,
            "drone_route",
            drone_route,
        )
        lines.append("  drone segments:")
        lines.append(
            "  from | to | distance | travel_time | arrival_time_at_to | "
            "service_start | service_finish | time_window | time_window_ok | "
            "delivery_load_departure | pickup_load_departure | effective_weight | "
            "flight_hours | delivered_at_to | load_after_service_at_to | "
            "energy_increment_kwh | cumulative_energy_kwh"
        )
        remaining_payload = payload
        sortie_customer_set = set(customers)
        for leg_idx in range(len(drone_route) - 1):
            start = drone_route[leg_idx]
            end = drone_route[leg_idx + 1]
            leg_distance = float(data.drone_distance_matrix[start, end])
            leg_travel_time = _travel_minutes(leg_distance, config.fleet.drone_speed_kmph)
            if end == recovery and leg_idx == len(drone_route) - 2:
                arrival_time = float(sortie.get("recovery_time", 0.0)) if isinstance(sortie, dict) else 0.0
            else:
                arrival_time = float(drone_arrival.get(end, 0.0))
            is_drone_customer = end in sortie_customer_set
            start_service = service_start.get(end, "") if is_drone_customer else ""
            finish_service = service_finish.get(end, "") if is_drone_customer else ""
            tw = data.time_windows.get(end, "") if is_drone_customer else ""
            tw_ok = ""
            if is_drone_customer and start_service != "":
                tw_ok = float(start_service) <= float(data.time_windows[end][1]) + 1e-9
            delivered = float(data.demands[end]) if is_drone_customer else 0.0
            load_departure = remaining_payload
            load_after_service = remaining_payload - delivered
            remaining_payload = load_after_service
            energy_row = energy_rows[leg_idx]
            lines.append(
                f"  {start} | {end} | {_fmt(leg_distance)} | {_fmt(leg_travel_time)} | "
                f"{_fmt(arrival_time)} | "
                f"{_fmt(start_service) if start_service != '' else ''} | "
                f"{_fmt(finish_service) if finish_service != '' else ''} | {tw} | {tw_ok} | "
                f"{_fmt(energy_row['delivery_load_departure'])} | "
                f"{_fmt(energy_row['pickup_load_departure'])} | "
                f"{_fmt(energy_row['effective_weight'])} | "
                f"{_fmt(energy_row['flight_hours'])} | "
                f"{_fmt(delivered)} | {_fmt(load_after_service)} | "
                f"{_fmt(energy_row['energy_increment'])} | {_fmt(energy_row['cumulative_energy'])}"
            )
            for field, value in {
                "sortie_id": sortie_idx,
                "from": start,
                "to": end,
                "distance": leg_distance,
                "travel_time": leg_travel_time,
                "arrival_time_at_to": arrival_time,
                "service_start": start_service,
                "service_finish": finish_service,
                "time_window": tw,
                "time_window_ok": tw_ok,
                "load_departure_from": load_departure,
                "delivery_load_departure": energy_row["delivery_load_departure"],
                "pickup_load_departure": energy_row["pickup_load_departure"],
                "effective_weight": energy_row["effective_weight"],
                "flight_hours": energy_row["flight_hours"],
                "delivered_at_to": delivered,
                "load_after_service_at_to": load_after_service,
                "energy_increment_kwh": energy_row["energy_increment"],
                "cumulative_energy_kwh": energy_row["cumulative_energy"],
            }.items():
                _append_csv_row(
                    csv_rows,
                    "drone_sorties",
                    "sortie_segment",
                    f"{sortie_idx}:{leg_idx + 1}",
                    field,
                    value,
                )
        lines.append("  drone customers:")
        lines.append(
            "  customer_id | arrival_time | service_start | service_finish | time_window | time_window_ok"
        )
        for customer in customers:
            start_service = float(service_start.get(customer, 0.0))
            finish_service = float(service_finish.get(customer, 0.0))
            arrival_time = float(drone_arrival.get(customer, 0.0))
            tw = data.time_windows[customer]
            tw_ok = start_service <= float(tw[1]) + 1e-9
            lines.append(
                f"  {customer} | {_fmt(arrival_time)} | {_fmt(start_service)} | "
                f"{_fmt(finish_service)} | {tw} | {tw_ok}"
            )
            for field, value in {
                "sortie_id": sortie_idx,
                "customer_id": customer,
                "arrival_time": arrival_time,
                "service_start": start_service,
                "service_finish": finish_service,
                "time_window": tw,
                "time_window_ok": tw_ok,
            }.items():
                _append_csv_row(
                    csv_rows,
                    "drone_sorties",
                    "sortie_customer",
                    f"{sortie_idx}:{customer}",
                    field,
                    value,
                )
        lines.append("")

    lines.append("四-补充、实体无人机路径")
    physical_routes = timing.get("drone_physical_routes", {})
    warehouse_launch_counts = timing.get("drone_warehouse_launch_count", {})
    if physical_routes:
        for drone_id, route in sorted(physical_routes.items()):
            lines.append(f"physical_drone_{int(drone_id)}: {' -> '.join(str(int(node)) for node in route)}")
            _append_csv_row(
                csv_rows,
                "physical_drones",
                "physical_drone",
                int(drone_id),
                "route",
                [int(node) for node in route],
            )
    else:
        lines.append("physical_drone_routes: []")
    lines.append("warehouse_launch_count per drone:")
    if warehouse_launch_counts:
        for drone_id, count in sorted(warehouse_launch_counts.items()):
            lines.append(f"physical_drone_{int(drone_id)}: {int(count)}")
            _append_csv_row(
                csv_rows,
                "physical_drones",
                "warehouse_launch_count",
                int(drone_id),
                "warehouse_launch_count",
                int(count),
            )
    else:
        lines.append("warehouse_launch_count: {}")
    lines.append("")

    lines.append("五、客户服务汇总")
    lines.append(
        "customer_id | service_mode | served_by_route_or_sortie_id | arrival_time | "
        "service_start | service_finish | time_window | demand | unique_service | mode_constraint_ok"
    )
    van_customer_set = set(state.get_van_customers())
    drone_customer_to_sortie = {}
    for sortie_idx, sortie in enumerate(state.drone_sorties, start=1):
        _, customers, _ = sortie_nodes(sortie)
        for customer in customers:
            drone_customer_to_sortie[customer] = sortie_idx

    for customer in data.customers:
        mode = state.service_mode.get(customer, "unknown")
        if customer in van_customer_set:
            served_by = "van_route"
            arrival_time = float(timing.get("van_arrival", {}).get(customer, 0.0))
        elif customer in drone_customer_to_sortie:
            served_by = f"drone_sortie_{drone_customer_to_sortie[customer]}"
            arrival_time = float(drone_arrival.get(customer, 0.0))
        else:
            served_by = "unserved"
            arrival_time = 0.0
        service_count = int(customer in van_customer_set) + int(customer in drone_customer_to_sortie)
        unique_service = service_count == 1
        mode_constraint_ok = not data.is_high_floor.get(customer, False) or mode == "drone"
        start_service = float(service_start.get(customer, 0.0))
        finish_service = float(service_finish.get(customer, 0.0))
        row = {
            "customer_id": customer,
            "service_mode": mode,
            "served_by_route_or_sortie_id": served_by,
            "arrival_time": arrival_time,
            "service_start": start_service,
            "service_finish": finish_service,
            "time_window": data.time_windows[customer],
            "demand": data.demands[customer],
            "unique_service": unique_service,
            "mode_constraint_ok": mode_constraint_ok,
        }
        lines.append(
            f"{customer} | {mode} | {served_by} | {_fmt(arrival_time)} | "
            f"{_fmt(start_service)} | {_fmt(finish_service)} | {data.time_windows[customer]} | "
            f"{data.demands[customer]} | {unique_service} | {mode_constraint_ok}"
        )
        for field, value in row.items():
            _append_csv_row(csv_rows, "customer_service", "customer", customer, field, value)
    lines.append("")

    lines.append("六、可行性检查结果")
    categories = {
        "time_window_violations": [
            item for item in timing.get("time_window_violations", [])
        ],
        "capacity_violations": [
            item for item in violations if "capacity" in item or "payload" in item
        ],
        "drone_endurance_violations": [
            item for item in violations if "endurance" in item
        ],
        "order_container_assignment_violations": [
            item
            for item in violations
            if "order" in item or "container" in item or "assignment" in item
        ],
        "launch_recovery_violations": [
            item
            for item in violations
            if "launch" in item or "recovery" in item or "van_route" in item
        ],
        "physical_drone_violations": [
            item
            for item in violations
            if "drone_id" in item or "physical drones" in item
        ],
    }
    lines.append(f"feasible: {feasible}")
    lines.append(f"violations: {violations}")
    for field, value in categories.items():
        lines.append(f"{field}: {value}")
        _append_csv_row(csv_rows, "feasibility", "category", field, field, value)
    _append_csv_row(csv_rows, "feasibility", "summary", "feasible", "feasible", feasible)
    _append_csv_row(csv_rows, "feasibility", "summary", "violations", "violations", violations)
    lines.append("")

    lines.append("七、成本拆分")
    lines.append(
        "drone_fixed_cost calculation: "
        f"used_drones({metrics.get('used_drones', 0)}) * "
        f"drone_fixed_cost({config.cost.drone_fixed_cost}) = "
        f"{_fmt(metrics.get('drone_fixed_cost', 0.0))}"
    )
    _append_csv_row(
        csv_rows,
        "costs",
        "calculation",
        "drone_fixed_cost",
        "calculation",
        {
            "used_drones": metrics.get("used_drones", 0),
            "unit_drone_fixed_cost": config.cost.drone_fixed_cost,
            "drone_fixed_cost": metrics.get("drone_fixed_cost", 0.0),
        },
    )
    cost_fields = [
        "truck_cost",
        "truck_transport_cost",
        "truck_fixed_cost",
        "van_cost",
        "van_transport_cost",
        "van_fixed_cost",
        "drone_cost",
        "drone_transport_cost",
        "drone_fixed_cost",
        "drone_energy",
        "penalty_cost",
        "total_cost",
        "waiting_cost_reported",
    ]
    for field in cost_fields:
        lines.append(f"{field}: {_fmt(metrics.get(field, 0.0))}")
        _append_csv_row(csv_rows, "costs", "cost", field, field, metrics.get(field, 0.0))
    lines.append("waiting_cost_reported 不进入 total_cost.")
    _append_csv_row(
        csv_rows,
        "costs",
        "note",
        "waiting_cost_reported",
        "not_in_total_cost",
        True,
    )
    lines.append("")

    txt_path = output_dir / "route_plan_detail.txt"
    csv_path = output_dir / "route_plan_detail.csv"
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["section", "row_type", "item_id", "field", "value"],
        )
        writer.writeheader()
        writer.writerows(csv_rows)


def evaluate_and_save(result: ALNSResult, data: InstanceData, config: TVDConfig) -> Dict[str, object]:
    output_dir = Path(config.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).resolve().parent / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    total, breakdown = objective(result.best_state, data, config)
    timing = compute_timing(result.best_state, data, config)
    total_van_waiting, total_drone_waiting = update_drone_sortie_timing(
        result.best_state, data, config
    )
    timing = result.best_state.timing
    feasible, violations = check_solution_feasible(result.best_state, data, config)
    timing = result.best_state.timing
    same_node_sorties = sum(
        1 for sortie in result.best_state.drone_sorties if sortie_nodes(sortie)[0] == sortie_nodes(sortie)[2]
    )
    cross_node_sorties = len(result.best_state.drone_sorties) - same_node_sorties
    drone_sortie_details = []
    for sortie in result.best_state.drone_sorties:
        launch, customers, recovery = sortie_nodes(sortie)
        payload = float(sum(data.demands[customer] for customer in customers))
        distance = drone_sortie_distance(sortie, data)
        energy = drone_sortie_energy(sortie, data, config)
        pickup_load_departure = 0.0
        effective_weight = payload + pickup_load_departure + config.fleet.drone_self_weight_kg
        drone_sortie_details.append(
            {
                "drone_id": int(sortie.get("drone_id", 0)) if isinstance(sortie, dict) else 0,
                "launch": launch,
                "launch_position": int(sortie.get("launch_position", -1)) if isinstance(sortie, dict) else -1,
                "customers": customers,
                "number_of_customers": len(customers),
                "recovery": recovery,
                "recovery_position": int(sortie.get("recovery_position", -1)) if isinstance(sortie, dict) else -1,
                "same_node": launch == recovery,
                "delivery_load_departure": payload,
                "pickup_load_departure": pickup_load_departure,
                "effective_weight": effective_weight,
                "flight_hours": distance / config.fleet.drone_speed_kmph,
                "energy_increment_kwh": energy,
                "cumulative_energy_kwh": energy,
                "total_payload": payload,
                "drone_distance": distance,
                "drone_energy": energy,
                "endurance_feasible": distance <= config.fleet.drone_endurance_km,
                "battery_feasible": energy <= config.fleet.drone_battery_capacity_kwh,
                "payload_feasible": payload <= config.fleet.drone_capacity_kg,
                "launch_time": float(sortie.get("launch_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "recovery_time": float(sortie.get("recovery_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "van_waiting_time": float(sortie.get("van_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "drone_waiting_time": float(sortie.get("drone_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            }
        )

    metrics: Dict[str, object] = {
        "best_objective": total,
        **breakdown,
        "runtime_seconds": result.runtime_seconds,
        "port_node": result.best_state.port_node,
        "truck_depot_node": result.best_state.truck_depot_node,
        "container_origin": result.best_state.container_origin,
        "transshipment_nodes": result.best_state.transshipment_nodes,
        "selected_transshipment": result.best_state.selected_transshipment,
        "candidate_transshipment_nodes": result.best_state.transshipment_nodes,
        "truck_arrival_time": timing.get("truck_arrival_time", 0.0),
        "van_start_time": timing.get("van_start_time", 0.0),
        "truck_arrival": timing.get("truck_arrival", {}),
        "van_arrival": timing.get("van_arrival", {}),
        "van_arrival_sequence": timing.get("van_arrival_sequence", []),
        "drone_arrival": timing.get("drone_arrival", {}),
        "service_start": timing.get("service_start", {}),
        "service_finish": timing.get("service_finish", {}),
        "time_windows": data.time_windows,
        "time_window_violations": timing.get("time_window_violations", []),
        "num_time_window_violations": len(timing.get("time_window_violations", [])),
        "total_early_waiting_time": timing.get("early_waiting_time", 0.0),
        "waiting_cost_reported": breakdown.get("waiting_cost_reported", 0.0),
        "waiting_cost_reported_not_optimized": True,
        "num_orders": len(result.best_state.order_assignment),
        "num_containers": len(result.best_state.container_assignment),
        "num_van_customers": len(result.best_state.get_van_customers()),
        "num_drone_customers": len(result.best_state.get_drone_customers()),
        "num_drone_sorties": len(result.best_state.drone_sorties),
        "number_of_same_node_sorties": same_node_sorties,
        "number_of_cross_node_sorties": cross_node_sorties,
        "total_van_waiting_time": total_van_waiting,
        "total_drone_waiting_time": total_drone_waiting,
        "drone_sortie_details": drone_sortie_details,
        "drone_physical_routes": timing.get("drone_physical_routes", {}),
        "drone_warehouse_launch_count": timing.get("drone_warehouse_launch_count", {}),
        "feasible": feasible,
        "violations": "; ".join(violations),
        "truck_route": result.best_state.truck_route,
        "van_route": result.best_state.van_route,
        "drone_sorties": result.best_state.drone_sorties,
        "container_assignment": result.best_state.container_assignment,
        "order_assignment": result.best_state.order_assignment,
        "route_plan_detail_txt": str(output_dir / "route_plan_detail.txt"),
        "route_plan_detail_csv": str(output_dir / "route_plan_detail.csv"),
    }

    save_convergence_plot(result.history, output_dir / "convergence.png")
    save_routes_plot(result.best_state, data, output_dir / "routes.png")
    save_route_plan_detail(result.best_state, data, config, metrics, output_dir)

    with (output_dir / "history.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(result.history[0].keys()))
        writer.writeheader()
        writer.writerows(result.history)

    with (output_dir / "summary.txt").open("w", encoding="utf-8") as file:
        for key, value in metrics.items():
            file.write(f"{key}: {value}\n")

    return metrics
