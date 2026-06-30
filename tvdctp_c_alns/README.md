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
- Payload-dependent drone energy checks for drone routes with delivery load
  and pickup load.
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
    "pickup_demand": ...,
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

The van route starts at `selected_transshipment` and may end at any candidate
transshipment warehouse. This is the toy project's open-route interpretation of
the paper's warehouse return flexibility:

```python
van_route = [selected_transshipment, ..., ending_transshipment]
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
    "launch_position": int,
    "recovery_position": int,
}
```

Drone sorties can continuously serve multiple customers when payload,
endurance, route order, strict customer time windows, and simplified
synchronization remain feasible. The code does not impose an artificial upper
bound on the number of customers in one sortie. Repair operators first try
cross-node sorties (`launch != recovery`). Same-node sorties are kept as a
fallback so small toy instances remain feasible.

Physical drone identities are assigned during timing propagation:

- `used_drones` is the number of physical drone ids used.
- `used_drone_sorties` is the number of independent flight sorties.
- `physical_drone_routes` reports the physical route of each drone, including
  carried movement from the warehouse to a later launch node when applicable.
- `warehouse_launch_count` counts each physical drone's departure from a
  warehouse. A drone carried away by a van without launching at the warehouse
  still counts as one warehouse departure.
- `warehouse_return_count` counts each physical drone's return to a warehouse.
- Each physical drone may depart from a warehouse at most once and return to a
  warehouse at most once. After returning to a warehouse, it cannot continue as
  the same physical drone in this toy model.

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
7. A recovered physical drone can be reused for a later sortie after recovery
   only if it was recovered at a non-warehouse van node. Recovery at a warehouse
   ends that physical drone route.

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

Important objective convention: `waiting_cost_reported` is not included in
`total_cost`, and drone energy is not converted into a monetary cost. Drone
energy is reported in kWh and used for battery feasibility only.

The current drone energy increment is:

```text
energy += [rou * (delivery_load + pickup_load + drone_self_weight) + rou1] * flight_hours
```

where delivery load decreases after customer delivery service and pickup load
increases after customer pickup service. The default toy data still uses
`pickup_demand=0`, `rou=0.5`, `rou1=0.18`, drone self-weight `5 kg`, and
battery capacity `13.8 kWh`.

`waiting_cost_reported` is diagnostic only and is not optimized directly.

## Not Implemented Yet

- Container splitting.
- Multiple containers.
- Multiple trucks, trailers, vans, or drones.
- Trailer-tractor binding.
- Multi-van cross-vehicle recovery.
- Gurobi MILP.
- RL/PPO operator selection.

Drone endurance is modeled both as a distance constraint and as a battery energy
constraint. Pickup load is implemented in load propagation and drone energy,
but the default toy data keeps pickup demand at zero unless configured
otherwise. Full import/export request classes and the second-stage export
container drayage are not implemented yet.

## Regression Tests / 回归测试

The regression tests are used to prevent future changes from breaking the paper
constraints that have already been implemented. They are not intended to prove
that ALNS finds the optimal solution. They do not assert a fixed route, and they
do not assert a fixed objective value. The tests mainly check feasibility,
constraints, cost formulas, and physical-drone rules.

Current tested instance sizes:

- tiny: `num_orders=6`, `num_transshipments=2`, `num_containers=1`
- small: `num_orders=10`, `num_transshipments=2`, `num_containers=1`
- medium: `num_orders=20`, `num_transshipments=3`, `num_containers=2`

Current checks:

- `feasible=True`
- `unassigned=[]`
- each customer is served exactly once
- `time_window_violations=[]`
- `total_cost > 0`
- `waiting_cost_reported` is not included in `total_cost`
- `used_drones` is counted by physical drone quantity
- `used_drone_sorties` equals the number of `drone_sorties`
- each physical drone has `warehouse_launch_count <= 1`
- each physical drone has `warehouse_return_count <= 1`
- drone payload, endurance, and energy are feasible

Run the regression tests from the `tvdctp_c_alns` directory:

```bash
python -m pytest tests
```

If `pytest` is not installed:

```bash
python -m pip install pytest
```

Run the regression tests after every change to `state.py`, `objective.py`,
`feasibility.py`, `operators.py`, `initial_solution.py`, `alns_solver.py`,
`evaluation.py`, `dataset_loader.py`, or `config.py`.

If you want tests to run automatically before `git commit`, manually configure a
pre-commit hook. This project does not write `.git/hooks` automatically.

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
