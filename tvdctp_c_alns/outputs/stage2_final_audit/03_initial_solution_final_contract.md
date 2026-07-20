# Initial Solution Final Contract

Status: **PASS / FROZEN**. The exact construction heuristic is an **APPROVED ENGINEERING DECISION** over paper-partial feasibility requirements.

1. Container destinations and stage-1 drayage are constructed first, with per-container assignment, tractor/trailer movement, unload-ready times, and warehouse resources.
2. Van construction uses only customers eligible for van service. Insertions must satisfy capacity, route timing/time windows, container readiness, and the current route/fleet scope.
3. Construction starts with one van per used warehouse and activates another configured van only after existing active routes cannot accept the customer. It does not balance into an unused van when one van remains feasible.
4. Multiple warehouses, vans, containers, and configured drones are represented explicitly in `TVDState`; flexible docking and cross-van recovery are canonical-checker capabilities used by feasible drone candidates.
5. High-floor customers are mandatory drone customers. Any such customer still on a van is removed and repaired by a hard-feasible drone sortie. A high-floor customer that cannot be legally drone-served remains unassigned and causes final construction failure; illegal van service is not a fallback.
6. Deferred ordinary customers may receive a drone attempt. Failed construction attempts are recorded and warned, but the final canonical checker controls the outcome. The function raises `ValueError` rather than silently returning an infeasible State.
7. Optional drone refinement is cost-aware for non-high-floor customers and mandatory for high-floor customers. Payload, endurance, energy, carrier/launch/recovery, synchronization, and time-window constraints are checked.
8. `objective()` is computed for metadata, then `check_solution_feasible()` is called explicitly. The State is returned only when canonical feasibility passes. `run_c_alns` independently rechecks the consolidated initial State and raises on failure.

Evidence:

- `tests/test_regression_rules.py` covers scalable construction, high-floor mandatory-drone service, infeasible high-floor rejection, capacity/time-window rejection, multi-van resources, multi-container assignment, docking, and timing.
- Stage 2A captured a reproducible initial State and explained objective differences by configuration/instance fingerprint, not by hidden algorithm drift.
- Stage 2F.2 full evidence passed all 294 nodes; both real main smokes constructed a feasible initial State.

Paper/engineering boundary:

- Model service eligibility and hard feasibility are paper/model obligations (**PAPER EXPLICIT/PARTIAL**).
- destination scoring, insertion order, van activation threshold/order, exact drone refinement, tie rules, and Python data structures are **APPROVED ENGINEERING DECISIONS**.
- The audit found no unresolved initial-solution correctness gap. It does not claim this heuristic is uniquely prescribed by the paper or produces a globally optimal initial State.
