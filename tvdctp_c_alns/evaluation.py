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
    delivery_demand,
    drone_sortie_distance,
    drone_sortie_energy,
    drone_sortie_energy_details,
    pickup_demand,
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
    return float(sum(delivery_demand(data, customer) for customer in served))


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
    sorties_by_recovery: Dict[int, List[dict]] = {}
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        recovery_pos = int(sortie.get("recovery_position", -1))
        if recovery_pos >= 0:
            sorties_by_recovery.setdefault(recovery_pos, []).append(sortie)
    delivery_load = _total_delivery_load(state, data)
    pickup_load = 0.0
    updates = []

    for route_index, node in enumerate(state.van_route):
        node = int(node)
        delivery_arrival = delivery_load
        pickup_arrival = pickup_load
        delivered = delivery_demand(data, node) if node in van_customers else 0.0
        picked_up = pickup_demand(data, node) if node in van_customers else 0.0
        delivery_load -= delivered
        pickup_load += picked_up
        launched_payload = float(
            sum(
                delivery_demand(data, customer)
                for sortie in sorties_by_launch.get(route_index, [])
                for customer in sortie_nodes(sortie)[1]
            )
        )
        delivery_load -= launched_payload
        recovered_pickup = float(
            sum(
                pickup_demand(data, customer)
                for sortie in sorties_by_recovery.get(route_index, [])
                for customer in sortie_nodes(sortie)[1]
            )
        )
        pickup_load += recovered_pickup
        updates.append(
            {
                "route_index": float(route_index),
                "node": float(node),
                "load_arrival": float(delivery_arrival + pickup_arrival),
                "delivery_load_arrival": float(delivery_arrival),
                "pickup_load_arrival": float(pickup_arrival),
                "delivered": float(delivered),
                "picked_up": float(picked_up),
                "launched_payload": float(launched_payload),
                "recovered_pickup": float(recovered_pickup),
                "delivery_load_departure": float(delivery_load),
                "pickup_load_departure": float(pickup_load),
                "load_departure": float(delivery_load + pickup_load),
            }
        )

    return updates


def _active_van_routes_for_detail(state: TVDState, data: InstanceData) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    active = _active_plot_van_routes(state, data)
    if active:
        return active
    return {
        str(van_id): [int(node) for node in route]
        for van_id, route in routes.items()
        if len(route) >= 2
    }


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


def _sortie_van_id(sortie: dict, field: str, fallback: str = "") -> str:
    if isinstance(sortie, dict) and sortie.get(field):
        return str(sortie[field])
    return fallback


def _van_has_drone_activity(state: TVDState, van_id: str) -> bool:
    for sortie in state.drone_sorties:
        if not isinstance(sortie, dict):
            continue
        launch_van = _sortie_van_id(sortie, "launch_van_id")
        recovery_van = _sortie_van_id(sortie, "recovery_van_id", launch_van)
        if van_id in {launch_van, recovery_van}:
            return True
    return False


def _active_plot_van_routes(state: TVDState, data: InstanceData) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    return {
        van_id: route
        for van_id, route in routes.items()
        if any(int(node) in data.customers for node in route)
        or _van_has_drone_activity(state, van_id)
    }


def _inactive_van_routes(state: TVDState, data: InstanceData) -> Dict[str, List[int]]:
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    active = set(_active_plot_van_routes(state, data))
    return {van_id: route for van_id, route in routes.items() if van_id not in active}


def save_routes_plot(state: TVDState, data: InstanceData, output_path: Path) -> None:
    width, height, pad = 900, 650, 55
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    points = _scale_points(data, width, height, pad)

    truck_route = state.truck_route
    for idx in range(len(truck_route) - 1):
        draw.line((points[truck_route[idx]], points[truck_route[idx + 1]]), fill=(214, 39, 40), width=3)

    van_colors = [
        (31, 119, 180),
        (23, 190, 207),
        (66, 133, 244),
        (0, 150, 136),
    ]
    routes = _active_plot_van_routes(state, data)
    for route_idx, (van_id, route) in enumerate(sorted(routes.items())):
        color = van_colors[route_idx % len(van_colors)]
        for idx in range(len(route) - 1):
            draw.line((points[route[idx]], points[route[idx + 1]]), fill=color, width=4)
        if route:
            x, y = points[route[0]]
            draw.text((x + 10, y + 10 + 12 * route_idx), van_id, fill=color)

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

    draw.text((pad, 20), "TVDCTP-T route: red=truck, blue/cyan=active van routes, green=drone", fill=(30, 30, 30))
    img.save(output_path)


def _drone_load_timeline_rows(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[Dict[str, object]]:
    timing = state.timing
    drone_arrival = timing.get("drone_arrival", {})
    rows: List[Dict[str, object]] = []

    for sortie_idx, sortie in enumerate(state.drone_sorties, start=1):
        launch, customers, recovery = sortie_nodes(sortie)
        energy, energy_rows = drone_sortie_energy_details(sortie, data, config)
        drone_id = str(sortie.get("drone_id", "")) if isinstance(sortie, dict) else ""
        launch_time = float(sortie.get("launch_time", 0.0)) if isinstance(sortie, dict) else 0.0
        recovery_time = float(sortie.get("recovery_time", 0.0)) if isinstance(sortie, dict) else 0.0
        launch_pos = int(sortie.get("launch_position", -1)) if isinstance(sortie, dict) else -1
        recovery_pos = int(sortie.get("recovery_position", -1)) if isinstance(sortie, dict) else -1
        launch_van_id = str(sortie.get("launch_van_id", "")) if isinstance(sortie, dict) else ""
        recovery_van_id = str(sortie.get("recovery_van_id", launch_van_id)) if isinstance(sortie, dict) else launch_van_id
        launch_delivery = float(sum(delivery_demand(data, customer) for customer in customers))
        launch_pickup = 0.0

        rows.append(
            {
                "sortie_id": sortie_idx,
                "drone_id": drone_id,
                "event": "launch",
                "node": launch,
                "route_leg": "",
                "launch_van_id": launch_van_id,
                "recovery_van_id": recovery_van_id,
                "van_position": launch_pos,
                "van_id": launch_van_id,
                "time": launch_time,
                "delivery_before": launch_delivery,
                "pickup_before": launch_pickup,
                "payload_before": launch_delivery + launch_pickup,
                "delivered": 0.0,
                "picked_up": 0.0,
                "delivery_after": launch_delivery,
                "pickup_after": launch_pickup,
                "payload_after": launch_delivery + launch_pickup,
                "energy_increment": 0.0,
                "cumulative_energy": 0.0,
                "capacity_feasible": launch_delivery + launch_pickup <= config.fleet.drone_capacity_kg + 1e-9,
                "battery_feasible": True,
            }
        )

        route = [launch] + customers + [recovery]
        for leg_idx, energy_row in enumerate(energy_rows):
            start = int(route[leg_idx])
            end = int(route[leg_idx + 1])
            is_recovery = leg_idx == len(energy_rows) - 1
            arrival_time = (
                recovery_time
                if is_recovery
                else float(drone_arrival.get(end, 0.0))
            )
            event = "recovery" if is_recovery else "serve_customer"
            rows.append(
                {
                    "sortie_id": sortie_idx,
                    "drone_id": drone_id,
                    "event": event,
                    "node": end,
                    "route_leg": f"{start}->{end}",
                    "launch_van_id": launch_van_id,
                    "recovery_van_id": recovery_van_id,
                    "van_position": recovery_pos if is_recovery else "",
                    "van_id": recovery_van_id if is_recovery else "",
                    "time": arrival_time,
                    "delivery_before": float(energy_row["delivery_load_departure"]),
                    "pickup_before": float(energy_row["pickup_load_departure"]),
                    "payload_before": float(energy_row["payload_departure"]),
                    "delivered": float(energy_row["delivered_at_to"]),
                    "picked_up": float(energy_row["picked_up_at_to"]),
                    "delivery_after": float(energy_row["delivery_load_after_service"]),
                    "pickup_after": float(energy_row["pickup_load_after_service"]),
                    "payload_after": float(energy_row["payload_after_service"]),
                    "energy_increment": float(energy_row["energy_increment"]),
                    "cumulative_energy": float(energy_row["cumulative_energy"]),
                    "capacity_feasible": float(energy_row["payload_after_service"]) <= config.fleet.drone_capacity_kg + 1e-9
                    and float(energy_row["payload_departure"]) <= config.fleet.drone_capacity_kg + 1e-9,
                    "battery_feasible": float(energy_row["cumulative_energy"]) <= config.fleet.drone_battery_capacity_kwh + 1e-9,
                }
            )

    return rows


def _van_load_timeline_rows(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
) -> List[Dict[str, object]]:
    timing = state.timing
    rows: List[Dict[str, object]] = []
    routes = state.van_routes if state.van_routes else {"van_0": state.van_route}
    sequences_by_van = timing.get("van_arrival_sequence_by_van", {})
    van_customers = set(state.get_van_customers())

    for van_id, route in sorted(routes.items()):
        sequence = {
            int(item["route_index"]): item
            for item in sequences_by_van.get(van_id, [])
            if isinstance(item, dict)
        }
        launches_by_pos: Dict[int, List[dict]] = {}
        recoveries_by_pos: Dict[int, List[dict]] = {}
        for sortie in state.drone_sorties:
            if not isinstance(sortie, dict):
                continue
            launch, customers, recovery = sortie_nodes(sortie)
            launch_van = str(sortie.get("launch_van_id", van_id))
            recovery_van = str(sortie.get("recovery_van_id", launch_van))
            if launch_van == van_id and launch in route:
                launches_by_pos.setdefault(route.index(launch), []).append(sortie)
            if recovery_van == van_id and recovery in route:
                recoveries_by_pos.setdefault(route.index(recovery), []).append(sortie)

        carried_customers = {
            int(node)
            for node in route
            if int(node) in van_customers
        }
        for sorties in launches_by_pos.values():
            for sortie in sorties:
                _, customers, _ = sortie_nodes(sortie)
                carried_customers.update(customers)

        delivery_load = float(sum(delivery_demand(data, customer) for customer in carried_customers))
        pickup_load = 0.0

        for route_index, node in enumerate(route):
            node = int(node)
            delivery_before = delivery_load
            pickup_before = pickup_load
            delivered = delivery_demand(data, node) if node in van_customers else 0.0
            picked_up = pickup_demand(data, node) if node in van_customers else 0.0
            delivery_load -= delivered
            pickup_load += picked_up
            launched_payload = float(
                sum(
                    delivery_demand(data, customer)
                    for sortie in launches_by_pos.get(route_index, [])
                    for customer in sortie_nodes(sortie)[1]
                )
            )
            delivery_load -= launched_payload
            recovered_pickup = float(
                sum(
                    pickup_demand(data, customer)
                    for sortie in recoveries_by_pos.get(route_index, [])
                    for customer in sortie_nodes(sortie)[1]
                )
            )
            pickup_load += recovered_pickup
            rows.append(
                {
                    "van_id": van_id,
                    "position": route_index,
                    "node": node,
                    "node_type": _node_type(node, data),
                    "time": float(sequence.get(route_index, {}).get("arrival_time", 0.0)),
                    "delivery_before": float(delivery_before),
                    "pickup_before": float(pickup_before),
                    "payload_before": float(delivery_before + pickup_before),
                    "van_delivered": float(delivered),
                    "van_picked_up": float(picked_up),
                    "drone_delivery_launched": float(launched_payload),
                    "drone_pickup_recovered": float(recovered_pickup),
                    "delivery_after": float(delivery_load),
                    "pickup_after": float(pickup_load),
                    "payload_after": float(delivery_load + pickup_load),
                    "capacity_feasible": float(delivery_load + pickup_load) <= config.fleet.van_capacity_kg + 1e-9,
                }
            )
    return rows


def _markdown_table(headers: List[str], rows: List[Dict[str, object]]) -> List[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = []
        for header in headers:
            value = row.get(header, "")
            values.append(_fmt(value) if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def save_load_timeline_markdown(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    metrics: Dict[str, object],
    output_path: Path,
) -> None:
    van_rows = _van_load_timeline_rows(state, data, config)
    drone_rows = _drone_load_timeline_rows(state, data, config)
    recovery_rows = [
        {
            "sortie_id": row["sortie_id"],
            "drone_id": row["drone_id"],
            "recovery_node": row["node"],
            "recovery_position": row["van_position"],
            "recovery_time": row["time"],
            "recovery_delivery_load": row["delivery_after"],
            "recovery_pickup_load": row["pickup_after"],
            "recovery_total_payload": row["payload_after"],
            "transferred_to_van": True,
        }
        for row in drone_rows
        if row.get("event") == "recovery"
    ]

    lines: List[str] = []
    lines.append("# TVDCTP-T Load Timeline")
    lines.append("")
    lines.append("All times are minutes. Loads are kilograms.")
    lines.append("D = delivery load, P = pickup load, T = total payload.")
    lines.append("")
    lines.append("## Summary")
    lines.extend(
        _markdown_table(
            ["field", "value"],
            [
                {"field": "feasible", "value": metrics.get("feasible", "")},
                {"field": "van_route", "value": " -> ".join(str(node) for node in state.van_route)},
                {"field": "used_drones", "value": metrics.get("used_drones", "")},
                {"field": "used_drone_sorties", "value": metrics.get("used_drone_sorties", "")},
                {"field": "total_cost", "value": metrics.get("total_cost", "")},
                {"field": "waiting_cost_reported", "value": metrics.get("waiting_cost_reported", "")},
                {"field": "drone_energy_kwh", "value": metrics.get("drone_energy", "")},
            ],
        )
    )
    lines.append("")

    lines.append("## Van Load Timeline")
    lines.extend(
        _markdown_table(
            [
                "position",
                "node",
                "node_type",
                "time",
                "delivery_before",
                "pickup_before",
                "payload_before",
                "van_delivered",
                "van_picked_up",
                "drone_delivery_launched",
                "drone_pickup_recovered",
                "delivery_after",
                "pickup_after",
                "payload_after",
                "capacity_feasible",
            ],
            van_rows,
        )
    )
    lines.append("")

    lines.append("## Drone Load Timeline")
    lines.extend(
        _markdown_table(
            [
                "sortie_id",
                "drone_id",
                "event",
                "node",
                "route_leg",
                "van_position",
                "time",
                "delivery_before",
                "pickup_before",
                "payload_before",
                "delivered",
                "picked_up",
                "delivery_after",
                "pickup_after",
                "payload_after",
                "energy_increment",
                "cumulative_energy",
                "capacity_feasible",
                "battery_feasible",
            ],
            drone_rows,
        )
    )
    lines.append("")

    lines.append("## Drone Recovery Load Summary")
    lines.extend(
        _markdown_table(
            [
                "sortie_id",
                "drone_id",
                "recovery_node",
                "recovery_position",
                "recovery_time",
                "recovery_delivery_load",
                "recovery_pickup_load",
                "recovery_total_payload",
                "transferred_to_van",
            ],
            recovery_rows,
        )
    )
    lines.append("")

    lines.append("## Physical Drone Routes")
    physical_routes = state.timing.get("drone_physical_routes", {})
    if physical_routes:
        for drone_id, route in sorted(physical_routes.items(), key=lambda item: str(item[0])):
            lines.append(f"- physical_{drone_id}: {' -> '.join(str(int(node)) for node in route)}")
    else:
        lines.append("- none")
    lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _arrow(draw: ImageDraw.ImageDraw, start: Tuple[int, int], end: Tuple[int, int], fill, width: int = 2) -> None:
    draw.line((start, end), fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length = max((dx * dx + dy * dy) ** 0.5, 1.0)
    ux = dx / length
    uy = dy / length
    size = 9
    left = (int(x2 - size * ux - size * 0.45 * uy), int(y2 - size * uy + size * 0.45 * ux))
    right = (int(x2 - size * ux + size * 0.45 * uy), int(y2 - size * uy - size * 0.45 * ux))
    draw.polygon([end, left, right], fill=fill)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    text: str,
    fill,
) -> None:
    text_box = draw.textbbox((0, 0), text)
    text_width = text_box[2] - text_box[0]
    draw.text((center_x - text_width // 2, y), text, fill=fill)


def _customer_demand_label(data: InstanceData, node: int) -> str:
    return f"({delivery_demand(data, node):.1f},{pickup_demand(data, node):.1f})"


def save_route_load_timeline_plot(
    state: TVDState,
    data: InstanceData,
    config: TVDConfig,
    output_path: Path,
) -> None:
    van_rows = _van_load_timeline_rows(state, data, config)
    drone_rows = _drone_load_timeline_rows(state, data, config)
    van_ids = sorted({str(row["van_id"]) for row in van_rows})
    max_route_len = max(
        (sum(1 for row in van_rows if str(row["van_id"]) == van_id) for van_id in van_ids),
        default=2,
    )
    width = max(1200, 180 * max(max_route_len, 2))
    drone_lane_gap = 110
    pad_x = 80
    y_top = 230
    van_lane_gap = 170
    drone_lane_offset = 70
    height = max(620, y_top + van_lane_gap * max(len(van_ids), 1) + 170)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    rows_by_van: Dict[str, List[Dict[str, object]]] = {
        van_id: sorted(
            [row for row in van_rows if str(row["van_id"]) == van_id],
            key=lambda row: int(row["position"]),
        )
        for van_id in van_ids
    }
    y_by_van = {
        van_id: y_top + van_idx * van_lane_gap
        for van_idx, van_id in enumerate(van_ids)
    }
    x_by_van_pos: Dict[Tuple[str, int], int] = {}
    for van_id, rows in rows_by_van.items():
        for idx, row in enumerate(rows):
            x_by_van_pos[(van_id, int(row["position"]))] = int(
                pad_x + idx / max(len(rows) - 1, 1) * (width - 2 * pad_x)
            )

    draw.text((pad_x, 28), "Route load timeline (D=delivery, P=pickup, T=total)", fill=(30, 30, 30))
    draw.text((pad_x, 48), f"Van capacity={config.fleet.van_capacity_kg:.1f} kg, Drone capacity={config.fleet.drone_capacity_kg:.1f} kg", fill=(80, 80, 80))

    van_colors = [(31, 119, 180), (23, 190, 207), (66, 133, 244), (0, 150, 136)]
    for van_idx, (van_id, rows) in enumerate(rows_by_van.items()):
        y_van = y_by_van[van_id]
        van_color = van_colors[van_idx % len(van_colors)]
        draw.text((pad_x, y_van - 58), van_id, fill=van_color)
        for idx in range(len(rows) - 1):
            p1 = (x_by_van_pos[(van_id, int(rows[idx]["position"]))], y_van)
            p2 = (x_by_van_pos[(van_id, int(rows[idx + 1]["position"]))], y_van)
            _arrow(draw, p1, p2, fill=van_color, width=3)

        for row in rows:
            x = x_by_van_pos[(van_id, int(row["position"]))]
            node = int(row["node"])
            is_wh = node in data.transshipment_nodes
            if node in data.customers:
                _draw_centered_text(
                    draw,
                    x,
                    y_van - 40,
                    _customer_demand_label(data, node),
                    fill=(35, 35, 35),
                )
            box = (x - 18, y_van - 18, x + 18, y_van + 18)
            fill = (255, 193, 7) if is_wh else (230, 240, 255)
            draw.rectangle(box, fill=fill, outline=(20, 20, 20), width=2)
            draw.text((x - 7, y_van - 7), str(node), fill=(0, 0, 0))
            draw.text((x - 45, y_van + 28), f"t={float(row['time']):.1f}", fill=(70, 70, 70))
            draw.text((x - 56, y_van + 44), f"D {float(row['delivery_after']):.1f}", fill=(31, 119, 180))
            draw.text((x - 56, y_van + 60), f"P {float(row['pickup_after']):.1f}", fill=(255, 127, 14))
            draw.text((x - 56, y_van + 76), f"T {float(row['payload_after']):.1f}", fill=(0, 0, 0))

    rows_by_sortie: Dict[int, List[Dict[str, object]]] = {}
    for row in drone_rows:
        rows_by_sortie.setdefault(int(row["sortie_id"]), []).append(row)

    colors = [(44, 160, 44), (148, 103, 189), (214, 39, 40), (23, 190, 207)]
    for sortie_idx, rows in sorted(rows_by_sortie.items()):
        color = colors[(sortie_idx - 1) % len(colors)]
        launch_row = rows[0]
        recovery_row = rows[-1]
        launch_van_id = str(launch_row.get("launch_van_id", launch_row.get("van_id", "")))
        recovery_van_id = str(recovery_row.get("recovery_van_id", recovery_row.get("van_id", launch_van_id)))
        y = y_by_van.get(launch_van_id, y_top) - drone_lane_offset
        positions: List[Tuple[int, int, Dict[str, object]]] = []
        recovery_y = y_by_van.get(recovery_van_id, y_by_van.get(launch_van_id, y_top)) - drone_lane_offset
        launch_x = x_by_van_pos.get((launch_van_id, int(launch_row.get("van_position", 0))), pad_x)
        recovery_x = x_by_van_pos.get((recovery_van_id, int(recovery_row.get("van_position", 0))), width - pad_x)
        same_anchor = launch_x == recovery_x and launch_van_id == recovery_van_id and len(rows) > 2
        for row_idx, row in enumerate(rows):
            if row_idx == 0:
                x = launch_x
                y_node = y
            elif row_idx == len(rows) - 1:
                x = recovery_x
                y_node = recovery_y
            else:
                if same_anchor:
                    x = min(width - pad_x, launch_x + 140 * row_idx)
                else:
                    x = int(launch_x + row_idx / max(len(rows) - 1, 1) * (recovery_x - launch_x))
                y_node = int(y + row_idx / max(len(rows) - 1, 1) * (recovery_y - y))
            positions.append((x, y_node, row))

        for idx in range(len(positions) - 1):
            x1, y1, _ = positions[idx]
            x2, y2, _ = positions[idx + 1]
            # Dashed drone leg.
            segments = 12
            for seg in range(segments):
                if seg % 2 == 0:
                    sx = int(x1 + (x2 - x1) * seg / segments)
                    sy = int(y1 + (y2 - y1) * seg / segments)
                    ex = int(x1 + (x2 - x1) * (seg + 1) / segments)
                    ey = int(y1 + (y2 - y1) * (seg + 1) / segments)
                    draw.line((sx, sy, ex, ey), fill=color, width=2)
            _arrow(draw, (x2 - 1, y2), (x2, y2), fill=color, width=1)

        for x, y_node, row in positions:
            node = int(row["node"])
            event = str(row["event"])
            event_label = {"launch": "L", "serve_customer": "C", "recovery": "R"}.get(event, event)
            if event == "serve_customer" and node in data.customers:
                _draw_centered_text(
                    draw,
                    x,
                    y_node - 54,
                    _customer_demand_label(data, node),
                    fill=(35, 35, 35),
                )
            if event in {"launch", "recovery"}:
                draw.rectangle((x - 15, y_node - 15, x + 15, y_node + 15), fill=(245, 255, 245), outline=color, width=2)
            else:
                draw.ellipse((x - 16, y_node - 16, x + 16, y_node + 16), fill=(245, 255, 245), outline=color, width=2)
            draw.text((x - 7, y_node - 7), str(node), fill=(0, 0, 0))
            draw.text((x - 18, y_node - 70 if event == "serve_customer" else y_node - 52), f"s{sortie_idx}-{event_label}", fill=color)
            draw.text((x - 45, y_node - 36), f"t={float(row['time']):.1f}", fill=(70, 70, 70))
            draw.text((x - 45, y_node + 22), f"D {float(row['delivery_after']):.1f}", fill=(31, 119, 180))
            draw.text((x - 45, y_node + 38), f"P {float(row['pickup_after']):.1f}", fill=(255, 127, 14))
            draw.text((x - 45, y_node + 54), f"T {float(row['payload_after']):.1f}", fill=(0, 0, 0))

    draw.text((pad_x, height - 48), "Solid line: van route. Dashed line: drone sortie. Customer labels above nodes show (delivery demand,pickup demand).", fill=(70, 70, 70))
    draw.text((pad_x, height - 30), "D/P/T values below nodes show load after service/transfer at that node.", fill=(70, 70, 70))
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
    service_start = timing.get("service_start", {})
    service_finish = timing.get("service_finish", {})
    drone_arrival = timing.get("drone_arrival", {})
    truck_arrival = timing.get("truck_arrival", {})
    truck_load_updates = _truck_load_updates(state, data)
    van_load_rows = _van_load_timeline_rows(state, data, config)

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
        "warehouse_num_vans": config.warehouse_num_vans(data.transshipment_nodes),
        "drones_per_van": config.fleet.drones_per_van,
        "warehouse_num_drones": config.warehouse_num_drones(data.transshipment_nodes),
        "owned_num_vans": config.total_num_vans(data.transshipment_nodes),
        "owned_num_drones": config.total_num_drones(data.transshipment_nodes),
        "van_home": state.van_home,
        "drone_initial_carrier": state.drone_initial_carrier,
        "drone_home_warehouse": state.drone_home_warehouse,
        "used_trucks": metrics.get("used_trucks", 0),
        "used_vans": metrics.get("used_vans", 0),
        "used_drones": metrics.get("used_drones", 0),
        "used_drone_sorties": metrics.get("used_drone_sorties", 0),
        "number_of_same_van_sorties": metrics.get("number_of_same_van_sorties", 0),
        "number_of_cross_van_sorties": metrics.get("number_of_cross_van_sorties", 0),
        "number_of_multi_customer_sorties": metrics.get("number_of_multi_customer_sorties", 0),
        "active_vans_for_routes_png": sorted(_active_plot_van_routes(state, data)),
        "inactive_vans_not_plotted": sorted(_inactive_van_routes(state, data)),
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
        "node_id | node_type | x | y | delivery_demand | pickup_demand | time_window | service_time | "
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
            "delivery_demand": data.demands.get(node, ""),
            "pickup_demand": getattr(data, "pickup_demands", {}).get(node, ""),
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
            f"{row['delivery_demand']} | {row['pickup_demand']} | {row['time_window']} | {row['service_time']} | "
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
    lines.append("van_routes by van_id:")
    for van_id, route in sorted(state.van_routes.items()):
        lines.append(f"{van_id}: {' -> '.join(str(node) for node in route)}")
        _append_csv_row(
            csv_rows,
            "van_routes",
            "van_route",
            van_id,
            "route",
            list(route),
        )
    inactive_routes = _inactive_van_routes(state, data)
    if inactive_routes:
        lines.append("inactive_van_routes_not_plotted:")
        for van_id, route in sorted(inactive_routes.items()):
            lines.append(f"{van_id}: {' -> '.join(str(node) for node in route)}")
            _append_csv_row(
                csv_rows,
                "van_routes",
                "inactive_van_route",
                van_id,
                "route",
                list(route),
            )
    lines.append("")
    active_routes_for_detail = _active_van_routes_for_detail(state, data)
    sequences_by_van = timing.get("van_arrival_sequence_by_van", {})
    load_rows_by_van_pos = {
        (str(row["van_id"]), int(row["position"])): row
        for row in van_load_rows
        if isinstance(row, dict)
    }

    for van_id, route in sorted(active_routes_for_detail.items()):
        sequence_by_pos = (
            {
                int(item["route_index"]): item
                for item in sequences_by_van.get(van_id, [])
                if isinstance(item, dict)
            }
            if isinstance(sequences_by_van, dict)
            else {}
        )
        lines.append(f"van_id: {van_id}")
        lines.append(f"route: {' -> '.join(str(node) for node in route)}")
        lines.append(
            "from | to | distance | travel_time | arrival_time_at_to | departure_time_from | "
            "service_start | service_finish | time_window | time_window_ok | "
            "load_departure_from | load_arrival_at_to | delivered_at_to | picked_up_at_to | "
            "launched_payload_at_to | recovered_pickup_at_to | load_departure_at_to"
        )
        for idx in range(len(route) - 1):
            start = int(route[idx])
            end = int(route[idx + 1])
            distance = float(data.ground_distance_matrix[start, end])
            travel_time = _travel_minutes(distance, config.fleet.van_speed_kmph)
            arrival_time = float(sequence_by_pos.get(idx + 1, {}).get("arrival_time", 0.0))
            departure_time_from = float(
                sequence_by_pos.get(idx, {}).get(
                    "departure_time",
                    sequence_by_pos.get(idx, {}).get("arrival_time", 0.0),
                )
            )
            tw = data.time_windows.get(end, "")
            start_service = service_start.get(end, "")
            finish_service = service_finish.get(end, "")
            tw_ok = ""
            if end in data.customers and start_service != "":
                tw_ok = float(start_service) <= float(data.time_windows[end][1]) + 1e-9
            start_load = load_rows_by_van_pos.get((van_id, idx), {})
            end_load = load_rows_by_van_pos.get((van_id, idx + 1), {})
            lines.append(
                f"{start} | {end} | {_fmt(distance)} | {_fmt(travel_time)} | {_fmt(arrival_time)} | "
                f"{_fmt(departure_time_from)} | "
                f"{_fmt(start_service) if start_service != '' else ''} | "
                f"{_fmt(finish_service) if finish_service != '' else ''} | {tw} | {tw_ok} | "
                f"{_fmt(start_load.get('payload_after', 0.0))} | "
                f"{_fmt(end_load.get('payload_before', 0.0))} | "
                f"{_fmt(end_load.get('van_delivered', 0.0))} | "
                f"{_fmt(end_load.get('van_picked_up', 0.0))} | "
                f"{_fmt(end_load.get('drone_delivery_launched', 0.0))} | "
                f"{_fmt(end_load.get('drone_pickup_recovered', 0.0))} | "
                f"{_fmt(end_load.get('payload_after', 0.0))}"
            )
            for field, value in {
                "van_id": van_id,
                "from": start,
                "to": end,
                "distance": distance,
                "travel_time": travel_time,
                "arrival_time_at_to": arrival_time,
                "departure_time_from": departure_time_from,
                "service_start": start_service,
                "service_finish": finish_service,
                "time_window": tw,
                "time_window_ok": tw_ok,
                "load_departure_from": start_load.get("payload_after", 0.0),
                "load_arrival_at_to": end_load.get("payload_before", 0.0),
                "delivered_at_to": end_load.get("van_delivered", 0.0),
                "picked_up_at_to": end_load.get("van_picked_up", 0.0),
                "launched_payload_at_to": end_load.get("drone_delivery_launched", 0.0),
                "recovered_pickup_at_to": end_load.get("drone_pickup_recovered", 0.0),
                "load_departure_at_to": end_load.get("payload_after", 0.0),
            }.items():
                _append_csv_row(
                    csv_rows,
                    "van_route",
                    "van_segment",
                    f"{van_id}:{idx + 1}",
                    field,
                    value,
                )
        lines.append("")

        lines.append(f"van node load updates ({van_id}):")
        lines.append(
            "van_id | route_index | node | delivery_arrival | pickup_arrival | load_arrival | "
            "delivered_here | picked_up_here | launched_delivery_here | recovered_pickup_here | "
            "delivery_departure | pickup_departure | load_departure"
        )
        for route_index in range(len(route)):
            update = load_rows_by_van_pos.get((van_id, route_index), {})
            node = int(route[route_index])
            lines.append(
                f"{van_id} | {route_index} | {node} | "
                f"{_fmt(update.get('delivery_before', 0.0))} | "
                f"{_fmt(update.get('pickup_before', 0.0))} | "
                f"{_fmt(update.get('payload_before', 0.0))} | "
                f"{_fmt(update.get('van_delivered', 0.0))} | "
                f"{_fmt(update.get('van_picked_up', 0.0))} | "
                f"{_fmt(update.get('drone_delivery_launched', 0.0))} | "
                f"{_fmt(update.get('drone_pickup_recovered', 0.0))} | "
                f"{_fmt(update.get('delivery_after', 0.0))} | "
                f"{_fmt(update.get('pickup_after', 0.0))} | "
                f"{_fmt(update.get('payload_after', 0.0))}"
            )
            for field, value in {
                "van_id": van_id,
                "route_index": route_index,
                "node": node,
                **update,
            }.items():
                _append_csv_row(
                    csv_rows,
                    "van_route",
                    "van_node_load",
                    f"{van_id}:{route_index}",
                    field,
                    value,
                )
        lines.append("")
    lines.append("")

    lines.append("四、无人机 sorties")
    for sortie_idx, sortie in enumerate(state.drone_sorties, start=1):
        launch, customers, recovery = sortie_nodes(sortie)
        launch_van_id = _sortie_van_id(sortie, "launch_van_id") if isinstance(sortie, dict) else ""
        recovery_van_id = (
            _sortie_van_id(sortie, "recovery_van_id", launch_van_id)
            if isinstance(sortie, dict)
            else launch_van_id
        )
        delivery_payload = float(sum(delivery_demand(data, customer) for customer in customers))
        pickup_payload = float(sum(pickup_demand(data, customer) for customer in customers))
        distance = drone_sortie_distance(sortie, data)
        energy, energy_rows = drone_sortie_energy_details(sortie, data, config)
        peak_payload = max(
            [0.0]
            + [
                max(float(row["payload_departure"]), float(row["payload_after_service"]))
                for row in energy_rows
            ]
        )
        flight_time = _travel_minutes(distance, config.fleet.drone_speed_kmph)
        launch_pos = int(sortie.get("launch_position", _route_position(state.van_route, launch))) if isinstance(sortie, dict) else _route_position(state.van_route, launch)
        recovery_pos = int(sortie.get("recovery_position", _route_position(state.van_route, recovery, launch_pos))) if isinstance(sortie, dict) else _route_position(state.van_route, recovery, launch_pos)
        van_arrival_by_van = timing.get("van_arrival_by_van", {})
        van_sequences_by_van = timing.get("van_arrival_sequence_by_van", {})
        recovery_sequence = (
            {
                int(item["route_index"]): item
                for item in van_sequences_by_van.get(recovery_van_id, [])
                if isinstance(item, dict)
            }
            if isinstance(van_sequences_by_van, dict)
            else {}
        )
        if isinstance(van_arrival_by_van, dict):
            van_arrival_recovery = float(
                van_arrival_by_van.get(recovery_van_id, {}).get(
                    int(recovery),
                    recovery_sequence.get(recovery_pos, {}).get("arrival_time", 0.0),
                )
            )
        else:
            van_arrival_recovery = float(
                recovery_sequence.get(recovery_pos, {}).get("arrival_time", 0.0)
            )
        delivery_load_departure = delivery_payload
        pickup_load_departure = 0.0
        effective_weight = (
            delivery_load_departure
            + pickup_load_departure
            + config.fleet.drone_self_weight_kg
        )
        van_waiting_time = float(sortie.get("van_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0
        drone_waiting_time = float(sortie.get("drone_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0
        sortie_fields = {
            "sortie_id": sortie_idx,
            "drone_id": str(sortie.get("drone_id", "")) if isinstance(sortie, dict) else "",
            "launch_van_id": launch_van_id,
            "recovery_van_id": recovery_van_id,
            "launch_node": launch,
            "launch_position": launch_pos,
            "launch_time": float(sortie.get("launch_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            "customers": customers,
            "recovery_node": recovery,
            "recovery_position": recovery_pos,
            "recovery_time": float(sortie.get("recovery_time", 0.0)) if isinstance(sortie, dict) else 0.0,
            "same_node": launch == recovery,
            "same_van_recovery": launch_van_id == recovery_van_id,
            "cross_van_recovery": launch_van_id != recovery_van_id,
            "delivery_load_departure": delivery_load_departure,
            "pickup_load_departure": pickup_load_departure,
            "effective_weight": effective_weight,
            "flight_hours": distance / config.fleet.drone_speed_kmph,
            "energy_increment_kwh": energy,
            "cumulative_energy_kwh": energy,
            "total_delivery_payload": delivery_payload,
            "total_pickup_payload": pickup_payload,
            "peak_payload": peak_payload,
            "payload": peak_payload,
            "total_drone_distance": distance,
            "total_drone_energy_kwh": energy,
            "energy": energy,
            "drone_flight_time": flight_time,
            "van_arrival_recovery": van_arrival_recovery,
            "van_waiting_time": van_waiting_time,
            "drone_waiting_time": drone_waiting_time,
            "waiting_time": van_waiting_time + drone_waiting_time,
            "endurance_feasible": distance <= config.fleet.drone_endurance_km,
            "battery_feasible": energy <= config.fleet.drone_battery_capacity_kwh,
            "payload_feasible": peak_payload <= config.fleet.drone_capacity_kg,
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
            "flight_hours | delivered_at_to | picked_up_at_to | payload_after_service_at_to | "
            "energy_increment_kwh | cumulative_energy_kwh"
        )
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
            delivered = delivery_demand(data, end) if is_drone_customer else 0.0
            picked_up = pickup_demand(data, end) if is_drone_customer else 0.0
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
                f"{_fmt(delivered)} | {_fmt(picked_up)} | "
                f"{_fmt(energy_row['payload_after_service'])} | "
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
                "load_departure_from": energy_row["payload_departure"],
                "delivery_load_departure": energy_row["delivery_load_departure"],
                "pickup_load_departure": energy_row["pickup_load_departure"],
                "payload_departure": energy_row["payload_departure"],
                "effective_weight": energy_row["effective_weight"],
                "flight_hours": energy_row["flight_hours"],
                "delivered_at_to": delivered,
                "picked_up_at_to": picked_up,
                "delivery_load_after_service": energy_row["delivery_load_after_service"],
                "pickup_load_after_service": energy_row["pickup_load_after_service"],
                "load_after_service_at_to": energy_row["payload_after_service"],
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
    warehouse_return_counts = timing.get("drone_warehouse_return_count", {})
    if physical_routes:
        for drone_id, route in sorted(physical_routes.items(), key=lambda item: str(item[0])):
            lines.append(f"physical_{drone_id}: {' -> '.join(str(int(node)) for node in route)}")
            _append_csv_row(
                csv_rows,
                "physical_drones",
                "physical_drone",
                str(drone_id),
                "route",
                [int(node) for node in route],
            )
    else:
        lines.append("physical_drone_routes: []")
    lines.append("warehouse_launch_count per drone:")
    if warehouse_launch_counts:
        for drone_id, count in sorted(warehouse_launch_counts.items(), key=lambda item: str(item[0])):
            lines.append(f"physical_{drone_id}: {int(count)}")
            _append_csv_row(
                csv_rows,
                "physical_drones",
                "warehouse_launch_count",
                str(drone_id),
                "warehouse_launch_count",
                int(count),
            )
    else:
        lines.append("warehouse_launch_count: {}")
    lines.append("warehouse_return_count per drone:")
    if warehouse_return_counts:
        for drone_id, count in sorted(warehouse_return_counts.items(), key=lambda item: str(item[0])):
            lines.append(f"physical_{drone_id}: {int(count)}")
            _append_csv_row(
                csv_rows,
                "physical_drones",
                "warehouse_return_count",
                str(drone_id),
                "warehouse_return_count",
                int(count),
            )
    else:
        lines.append("warehouse_return_count: {}")
    lines.append("")

    lines.append("五、客户服务汇总")
    lines.append(
        "customer_id | service_mode | served_by_route_or_sortie_id | arrival_time | "
        "service_start | service_finish | time_window | delivery_demand | pickup_demand | "
        "unique_service | mode_constraint_ok"
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
            "delivery_demand": delivery_demand(data, customer),
            "pickup_demand": pickup_demand(data, customer),
            "unique_service": unique_service,
            "mode_constraint_ok": mode_constraint_ok,
        }
        lines.append(
            f"{customer} | {mode} | {served_by} | {_fmt(arrival_time)} | "
            f"{_fmt(start_service)} | {_fmt(finish_service)} | {data.time_windows[customer]} | "
            f"{delivery_demand(data, customer)} | {pickup_demand(data, customer)} | "
            f"{unique_service} | {mode_constraint_ok}"
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
    same_van_sorties = 0
    cross_van_sorties = 0
    multi_customer_sorties = 0
    drone_sortie_details = []
    for sortie_idx, sortie in enumerate(result.best_state.drone_sorties, start=1):
        launch, customers, recovery = sortie_nodes(sortie)
        launch_van_id = _sortie_van_id(sortie, "launch_van_id") if isinstance(sortie, dict) else ""
        recovery_van_id = (
            _sortie_van_id(sortie, "recovery_van_id", launch_van_id)
            if isinstance(sortie, dict)
            else launch_van_id
        )
        same_van_sorties += int(launch_van_id == recovery_van_id)
        cross_van_sorties += int(launch_van_id != recovery_van_id)
        multi_customer_sorties += int(len(customers) > 1)
        delivery_payload = float(sum(delivery_demand(data, customer) for customer in customers))
        pickup_payload = float(sum(pickup_demand(data, customer) for customer in customers))
        distance = drone_sortie_distance(sortie, data)
        energy = drone_sortie_energy(sortie, data, config)
        _, energy_rows = drone_sortie_energy_details(sortie, data, config)
        peak_payload = max(
            [0.0]
            + [
                max(float(row["payload_departure"]), float(row["payload_after_service"]))
                for row in energy_rows
            ]
        )
        pickup_load_departure = 0.0
        effective_weight = delivery_payload + pickup_load_departure + config.fleet.drone_self_weight_kg
        drone_sortie_details.append(
            {
                "sortie_id": sortie_idx,
                "drone_id": str(sortie.get("drone_id", "")) if isinstance(sortie, dict) else "",
                "launch_van_id": launch_van_id,
                "recovery_van_id": recovery_van_id,
                "launch": launch,
                "launch_position": int(sortie.get("launch_position", -1)) if isinstance(sortie, dict) else -1,
                "customers": customers,
                "number_of_customers": len(customers),
                "recovery": recovery,
                "recovery_position": int(sortie.get("recovery_position", -1)) if isinstance(sortie, dict) else -1,
                "same_node": launch == recovery,
                "same_van_recovery": launch_van_id == recovery_van_id,
                "cross_van_recovery": launch_van_id != recovery_van_id,
                "delivery_load_departure": delivery_payload,
                "pickup_load_departure": pickup_load_departure,
                "effective_weight": effective_weight,
                "flight_hours": distance / config.fleet.drone_speed_kmph,
                "energy_increment_kwh": energy,
                "cumulative_energy_kwh": energy,
                "total_delivery_payload": delivery_payload,
                "total_pickup_payload": pickup_payload,
                "peak_payload": peak_payload,
                "payload": peak_payload,
                "drone_distance": distance,
                "drone_energy": energy,
                "energy": energy,
                "endurance_feasible": distance <= config.fleet.drone_endurance_km,
                "battery_feasible": energy <= config.fleet.drone_battery_capacity_kwh,
                "payload_feasible": peak_payload <= config.fleet.drone_capacity_kg,
                "launch_time": float(sortie.get("launch_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "recovery_time": float(sortie.get("recovery_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "van_waiting_time": float(sortie.get("van_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "drone_waiting_time": float(sortie.get("drone_waiting_time", 0.0)) if isinstance(sortie, dict) else 0.0,
                "waiting_time": (
                    float(sortie.get("van_waiting_time", 0.0))
                    + float(sortie.get("drone_waiting_time", 0.0))
                    if isinstance(sortie, dict)
                    else 0.0
                ),
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
        "warehouse_num_vans": config.warehouse_num_vans(data.transshipment_nodes),
        "drones_per_van": config.fleet.drones_per_van,
        "warehouse_num_drones": config.warehouse_num_drones(data.transshipment_nodes),
        "van_home": result.best_state.van_home,
        "drone_initial_carrier": result.best_state.drone_initial_carrier,
        "drone_home_warehouse": result.best_state.drone_home_warehouse,
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
        "number_of_same_van_sorties": same_van_sorties,
        "number_of_cross_van_sorties": cross_van_sorties,
        "number_of_multi_customer_sorties": multi_customer_sorties,
        "total_van_waiting_time": total_van_waiting,
        "total_drone_waiting_time": total_drone_waiting,
        "drone_sortie_details": drone_sortie_details,
        "drone_physical_routes": timing.get("drone_physical_routes", {}),
        "drone_warehouse_launch_count": timing.get("drone_warehouse_launch_count", {}),
        "drone_warehouse_return_count": timing.get("drone_warehouse_return_count", {}),
        "feasible": feasible,
        "violations": "; ".join(violations),
        "truck_route": result.best_state.truck_route,
        "van_route": result.best_state.van_route,
        "van_routes": result.best_state.van_routes,
        "drone_sorties": result.best_state.drone_sorties,
        "container_assignment": result.best_state.container_assignment,
        "order_assignment": result.best_state.order_assignment,
        "route_plan_detail_txt": str(output_dir / "route_plan_detail.txt"),
        "route_plan_detail_csv": str(output_dir / "route_plan_detail.csv"),
        "load_timeline_md": str(output_dir / "load_timeline.md"),
        "route_load_timeline_png": str(output_dir / "route_load_timeline.png"),
    }

    save_convergence_plot(result.history, output_dir / "convergence.png")
    save_routes_plot(result.best_state, data, output_dir / "routes.png")
    save_route_plan_detail(result.best_state, data, config, metrics, output_dir)
    save_load_timeline_markdown(
        result.best_state,
        data,
        config,
        metrics,
        output_dir / "load_timeline.md",
    )
    save_route_load_timeline_plot(
        result.best_state,
        data,
        config,
        output_dir / "route_load_timeline.png",
    )

    with (output_dir / "history.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(result.history[0].keys()))
        writer.writeheader()
        writer.writerows(result.history)

    with (output_dir / "summary.txt").open("w", encoding="utf-8") as file:
        for key, value in metrics.items():
            file.write(f"{key}: {value}\n")

    return metrics
