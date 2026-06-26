# TVDCTP-T C-ALNS Toy Project

This project is a readable Python toy implementation for the paper problem:
**Truck-Van-Drone Collaborative Transportation Problem with Transshipment
(TVDCTP-T)**.

## Current v6 Scope

The current v6 toy version models:

- 1 container.
- 6 orders/customers by default.
- 1 truck depot.
- 1 port node.
- 2 candidate transshipment warehouses.
- 1 selected transshipment warehouse.
- 1 van route and simplified drone sorties.
- Physical drone identities assigned across sorties for fixed-cost counting.
- Payload-dependent drone energy checks for delivery-only drone routes.
- Strict customer time windows.
- Arrival-time propagation for truck, van, and drone moves.
- Simplified van-drone timing synchronization.
- A selected-transshipment switch destroy operator inside ALNS.
- Vehicle fixed usage costs plus distance-based transportation costs.

The container is **not split**. All orders belong to container `0`, and the
container is assigned to exactly one selected transshipment warehouse.

## Default Node Numbering

| Node | Meaning |
| --- | --- |
| `0` | Port node. |
| `1` | Truck/tractor depot node. |
| `2, 3` | Candidate transshipment warehouses. |
| `4..9` | Customer/order service nodes. |

## Container and Order Semantics

Each order is stored in `order_assignment`:

```python
order_assignment[customer_id] = {
    "order_id": ...,
    "customer_id": customer_id,
    "container_id": 0,
    "container_origin": container_origin,
    "assigned_transshipment": selected_transshipment,
    "demand": ...,
    "service_required": True,
}
```

The single toy container is stored in `container_assignment`:

```python
container_assignment[0] = {
    "container_id": 0,
    "origin_node": container_origin,
    "origin_type": "port" or "transshipment",
    "candidate_transshipments": [2, 3],
    "selected_transshipment": selected_transshipment,
    "orders": [0, 1, 2, 3, 4, 5],
    "customers": [4, 5, 6, 7, 8, 9],
}
```

## Route Semantics

The truck route is based on the selected transshipment:

```python
truck_route = [truck_depot_node, container_origin, selected_transshipment]
```

If the container is already at the selected transshipment, the route is
simplified to:

```python
truck_route = [truck_depot_node, selected_transshipment]
```

The van route starts and ends at `selected_transshipment`:

```python
van_route = [selected_transshipment, ..., selected_transshipment]
```

Drone sorties keep the format:

```python
{
    "launch": int,
    "customers": [customer_1, customer_2, ...],
    "recovery": int,
    "launch_time": float,
    "recovery_time": float,
    "van_waiting_time": float,
    "drone_waiting_time": float,
    "same_node": bool,
    "drone_id": int,
}
```

Drone sorties can continuously serve multiple customers when payload,
endurance, route order, strict customer time windows, and simplified
synchronization remain feasible. The code does not impose an artificial upper
bound on the number of customers in one sortie. Repair operators first try
cross-node sorties (`launch != recovery`). Same-node sorties are kept as a
fallback so small toy instances remain feasible.

High-floor customers are input parameters and must be served by drone.
Low-floor customers are allowed to be served by either van or drone; the final
`service_mode` is an optimization decision. In the current toy data,
`drone_eligible=True` for every customer, while high-floor status only imposes
the mandatory drone-service rule.

## What ALNS Optimizes

In this v6 toy version, the initial solution chooses `selected_transshipment`
using a simple estimated-cost rule. The ALNS loop optimizes:

- `van_route`
- `drone_sorties`
- `service_mode`
- `unassigned`
- `selected_transshipment`

The `switch_transshipment_operator` can move a candidate solution to another
candidate warehouse. It rebuilds `truck_route`, resets customer service, updates
`order_assignment` and `container_assignment`, and then lets the selected repair
operator rebuild the van route and drone sorties. Infeasible switched candidates
are rejected by the ALNS acceptance logic.

## Strict Time Windows and Timing

All propagated times are in minutes. Distances are kilometers and speeds are
kilometers/hour.

Each customer has:

```python
time_windows[customer] = (earliest, latest)
service_times[customer] = service_time_minutes
```

The current toy default uses `service_time_minutes = 0.0`, matching the model
assumption that van customer service time is ignored. Drone launch/recovery and
battery replacement times are also ignored; a sortie can launch when the van
arrives at the launch node.

Customer time windows are hard constraints:

- Early arrival is allowed; the vehicle or drone waits until `earliest`.
- Late service is not allowed.
- If `service_start > latest`, `check_solution_feasible` returns
  `feasible=False`.
- Time-window violations are not softened by a time-window penalty.

The timing propagation computes:

- Truck arrival along `truck_route`.
- `truck_arrival_time` at `selected_transshipment`, which is also the earliest
  van start time.
- Van arrival and service start/finish along `van_route`.
- Drone customer arrival and service start/finish along each sortie.
- Van/drone waiting time at recovery nodes.
- Early waiting time caused by arriving before a customer window opens.

For each drone sortie:

1. `launch_time` is the later of van availability and assigned drone availability
   at the launch node.
2. Drone flight time is computed as
   `launch -> customer_1 -> customer_2 -> ... -> recovery`.
3. Drone customers are served in sortie order with hard time-window checks.
4. Van arrival at the recovery node is read from the propagated van route.
5. If the drone arrives later, `van_waiting_time` is positive.
6. If the van arrives later, `drone_waiting_time` is positive.
7. A recovered physical drone can be reused for a later sortie after recovery.

The waiting cost uses the sum of van and drone waiting minutes converted to the
configured hourly waiting cost. It is reported as `waiting_cost_reported`, but
it is not added to `total_cost`.

## Cost Breakdown

The objective contains:

- `truck_cost`
- `truck_transport_cost`
- `truck_fixed_cost`
- `van_cost`
- `van_transport_cost`
- `van_fixed_cost`
- `drone_cost`
- `drone_transport_cost`
- `drone_fixed_cost`
- `drone_energy`
- `waiting_cost_reported`
- `penalty_cost`
- `total_cost`

The truck cost is computed from `truck_route`, not from a fixed
`port -> transshipment` shortcut.

`total_cost` contains only:

- `truck_cost`
- `van_cost`
- `drone_cost`
- `penalty_cost`

where each vehicle-mode cost is fixed usage cost plus distance-based
transportation cost. Truck and van usage are binary route activations. Drone
usage is counted by unique physical `drone_id` assigned during timing
propagation, while `used_drone_sorties` is reported separately.

The current delivery-only drone energy increment is:

```text
energy += [rou * (delivery_load + pickup_load + drone_self_weight) + rou1] * flight_hours
```

with pickup load currently zero, `rou=0.5`, `rou1=0.18`, drone self-weight
`5 kg`, and battery capacity `13.8 kWh`.

`waiting_cost_reported` is diagnostic only and is not optimized directly.

## Not Implemented Yet

- Container splitting.
- Multiple containers.
- Multiple trucks, trailers, vans, or drones.
- Trailer-tractor binding.
- Pickup/delivery request types.
- Multi-van cross-vehicle recovery.
- Gurobi MILP.
- RL/PPO operator selection.

Drone endurance is modeled both as a distance constraint and as a battery energy
constraint. Pickup load is not implemented yet.

## How to Run

From the `ALNS` root directory:

```bash
python tvdctp_c_alns/main.py --num_orders 6 --num_transshipments 2 --num_containers 1 --container_origin port --iterations 100
```

The project venv command is:

```bash
D:\STUDY\STUDY\PythonProject\.venv\Scripts\python.exe tvdctp_c_alns\main.py --num_orders 6 --num_transshipments 2 --num_containers 1 --container_origin port --iterations 100
```

Outputs are saved to:

- `outputs/convergence.png`
- `outputs/routes.png`
- `outputs/history.csv`
- `outputs/summary.txt`
