# Objective, Checker, Timing, and State Contract

## Objective

`objective()` computes tractor/trailer transport and fixed costs, van transport/fixed costs, drone transport/fixed costs, and an infeasibility penalty. Waiting minutes/cost are reported in the breakdown but deliberately excluded from `total_cost`. Physical drones and drone sorties are counted separately. The objective calls the canonical checker and records feasibility/violations on the State.

## Canonical checker and timing

`check_solution_feasible()` is production code and the canonical hard-feasibility boundary, not test instrumentation. It checks service completeness/uniqueness, eligibility, capacities/resources, routes/assignments, drone flight/energy/physical carrier continuity, synchronization, container readiness, flexible docking, and hard time windows. `compute_timing()` propagates the authoritative stage/van/drone arrival, service, waiting, launch/recovery, and violation state used by the checker.

Objective and checker may repeat timing/check work across candidates; Stage 2E diagnosed that cost. Test instrumentation only counts and traces production calls. It never substitutes for or changes checker results.

## State

`TVDState` owns stage-1 and stage-2 routes, homes/resources, container/order assignments, service modes, unassigned customers, drone sorties, metadata, and timing. `cache_signature()`/business fingerprints represent business State and exclude ephemeral context. `copy()` isolates mutable solution data; the only shared removal context is fully immutable and is consumed at the repair boundary.

Persistent `initial`, `current`, and `best` States must never carry active `RemovalStructuralContext`. Solver assertions and lifecycle tests enforce this before selection, after repair, and at return. Cascade metadata is validated against exact destroyed-State fingerprints and cleared on all repair returns.

Frozen Git blobs (all exact at `172166ee`):

| File | Blob |
|---|---|
| `objective.py` | `bd94b9bc76d11a1ee7b5234d2625f516bacbb00a` |
| `feasibility.py` | `a9494e7874cc650e9af5a90f2760333a62d0e49d` |
| `state.py` | `40bad0e83fcd08dfc4243837abb2482ed2052822` |

Classification: feasibility/model constraints are **PAPER EXPLICIT/PARTIAL**; exact State schema, caching, fingerprints, context lifecycle, and checker/timing architecture are **APPROVED ENGINEERING DECISIONS**.
