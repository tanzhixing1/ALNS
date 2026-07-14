# Candidate enumeration before and after

## Code path

Both repair families share
`_enumerate_feasible_drone_moves_for_customers()`:

- Stage 2C Regret reaches it through `_enumerate_feasible_drone_moves()` and
  passes a single-customer list.
- Stage 2D Cascade calls it for the bundle `dependency_order`, so all bundle
  customers enter one sortie.

The cost-oriented `_best_drone_move_for_customers()` had the same first-drone
selection and was repaired consistently.

## Before

For each launch van, the code selected exactly one ID with
`_first_drone_for_van()`. If that concrete ID failed hard feasibility, no other
drone on the same carrier was tried.

## After

`_candidate_drones_for_launch_van()` produces a deterministic, named-resource
necessary-condition superset. Each concrete ID is then placed into the existing
launch-position/recovery-van/recovery-position loops and evaluated by the
unchanged `_drone_insert_hard_feasible()` path. Exact carrier, existing-task,
availability-time, sortie-order, warehouse-return, capacity, energy, and timing
rules remain in the existing hard checker. Only feasible moves are returned.

The identity and local cache key already include `drone_id`. No cost-based
deduplication, symmetry pruning, top-K, beam, or candidate cutoff was added.

## Fixed-fixture count change

| Bundle | Source | Before | After |
| --- | --- | ---: | ---: |
| 0000 | snapshot | 1 | 1 |
| 0000 | van block | 2 | 2 |
| 0000 | drone bundle | 3 | 6 |
| 0000 | raw / feasible / unique | 6 / 6 / 6 | 9 / 9 / 9 |
| 0001 | snapshot | 1 | 1 |
| 0001 | van block | 7 | 7 |
| 0001 | drone bundle | 46 | 92 |
| 0001 | raw / feasible / unique | 54 / 54 / 54 | 100 / 100 / 100 |

The fixture has two symmetric initially carried drones. Drone candidates double
because both concrete named strategies are now retained. Snapshot and van-block
families are unchanged. In every run, `unique <= feasible <= raw`.
