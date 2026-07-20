# Default vs Explicit Paper Entry

Both runs used the bundled Python runtime because the shell's default `python` lacked NumPy. Both invoked the real `tvdctp_c_alns/main.py` entry.

Default command omitted `--operator-mode`; explicit command used `--operator-mode paper_mode`. Both used 20 orders, 20 customers, 2 containers, 2 transshipments, 5 iterations, and seed 42.

## Resolved configuration

| Field | Default | Explicit |
| --- | --- | --- |
| num_orders | 20 | 20 |
| num_customers | 20 | 20 |
| num_containers | 2 | 2 |
| num_transshipments | 2 | 2 |
| iterations | 5 | 5 |
| seed | 42 | 42 |
| operator_mode | paper_mode | paper_mode |
| warehouse_num_vans | `{3: 3, 4: 3}` | `{3: 3, 4: 3}` |
| drones_per_van | 2 | 2 |
| max_drones_carried_per_van | 3 | 3 |
| high_floor_ratio | 0.35 | 0.35 |
| max_no_improve | 100 | 100 |

## Deterministic comparison

| Field | Result |
| --- | --- |
| process exit codes | 0 / 0 |
| resolved mode | paper_mode / paper_mode |
| action count | 16 / 16 |
| registry fingerprint | `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1` / same |
| ordered action mapping | equal |
| initial objective | 1484.4917238190928 / same |
| initial solution fingerprint | `f2a3c106f1b9abef00cbd338bd25e7b927d7bb1784e51a8cd440132a0188f524` / same |
| destroy sequence | `[cascade_aware_removal, cascade_aware_removal, random_customer_removal, greedy_removal, random_customer_removal]` / same |
| repair sequence | `[greedy_van_repair, greedy_van_repair, greedy_van_repair, best_mode_repair, greedy_van_repair]` / same |
| action ID sequence | `[13, 13, 1, 4, 1]` / same |
| acceptance sequence | `[False, False, False, True, False]` / same |
| best-objective sequence | `[1484.4917238190928, 1484.4917238190928, 1484.4917238190928, 1465.9853751167163, 1465.9853751167163]` / same |
| final objective | 1465.9853751167163 / same |
| final business fingerprint | `ea6f69f47524fbc53380b24c8c3647bf459a25de98dd4c799bd98b30b79f8ce2` / same |
| feasibility / violations | True / none, equal |

The two `history.csv` files and two `route_plan_detail.csv` files are byte-for-byte equal. The RNG observable digest is `52615293f92efbf79296fb66adb9d5462aacfab64292a594fc2dabba8c5e2b53` for both runs. This digest covers ordered selections, action IDs, acceptance decisions, and objective fields; production `main.py` does not persist the NumPy bit-generator internal state, so this is explicitly an observable-trace digest rather than an internal RNG-state digest.

Wall time differed, as allowed: default 12.338813500 seconds; explicit 12.263523600 seconds.

**DEFAULT PAPER ENTRY CONTRACT PASS**
