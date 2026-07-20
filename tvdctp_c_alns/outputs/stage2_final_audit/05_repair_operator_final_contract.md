# Four Repair Operators — Final Contract

## Global Repair (`best_mode_repair`)

- Enumerates the complete currently supported hard-feasible van and drone insertion set for each unassigned customer.
- Compares concrete moves by objective/cost and stable move identity; applies the best supported move and recomputes as the State changes.
- Candidate generation includes all configured legal drones and legal cross-van recovery.
- If no candidate exists, the customer remains unassigned; there is no hidden infeasible insertion.
- Classification: **PAPER PARTIAL + APPROVED ENGINEERING DECISION**.

## Local Repair (`greedy_van_repair`, paper display `Local`)

- Selects one deterministic target van route per customer.
- Van insertion is restricted to that route; drone launch scope is restricted to it.
- Legal recovery on a different van remains available, preserving flexible docking.
- A target-scope failure stays unassigned; it does not scan a cheaper/feasible global route. Global default helpers remain unrestricted.
- Classification: **PAPER PARTIAL + APPROVED ENGINEERING DECISION**. Target selection and tie mechanics are engineering details.

## True Regret-2 (`regret_repair`)

- Enumerates every unique supported hard-feasible concrete van/drone insertion move; no mode-level shortcut, top-K, beam, sampling, or lossy truncation.
- The first and second choices are taken from the full concrete set and may be van/van, drone/drone, van/drone, or drone/van.
- Each move is scored by exact objective delta. `Regret(i)=f2-f1`; the maximum-regret customer is selected and its best move applied, then all remaining evaluations are recomputed.
- Single-candidate and exact-tie behavior is deterministic; stable ordering includes van-before-drone where the approved identity rule applies.
- Semantic contract: frozen. Runtime: not solved. Stage 2E.2 measured only 6.78% median wall improvement in a reverted exact-cache prototype, so no performance code entered the baseline.

## Cascade Repair (`cascade_repair`)

- Detaches/consumes context at the public boundary. Native contracts bypass the adapter; ordinary Random/Greedy/Related contexts are lazily adapted only for their Cascade pair.
- Validated bundles are processed atomically in stable order. Ω(B) contains exact snapshot reconstruction, every affected-segment contiguous all-van block, and every affected-scope whole-bundle drone move.
- No per-customer Cartesian product, approximation, top-K, beam, or candidate truncation is used.
- Each raw strategy must stay inside the affected boundary and pass the production canonical checker, permitting only the exact later-bundle unassigned set.
- Feasible unique strategies receive full objective scoring; complete stable identity resolves exact objective ties.
- Empty Ψ(B), invalid/stale context, malformed contract, or later-bundle failure returns the atomic failure State—no partial first-bundle commit and no fallback to another repair.
- Context and stale Cascade metadata are cleared on every success/failure return.
- Ω(B) construction, stable identities, ordering, and empty-set behavior are **APPROVED ENGINEERING DECISIONS** over a **PAPER PARTIAL** joint-repair contract.

Evidence: Stage 2B/2C focused suites; Stage 2D.0/2D.1 contracts; multi-drone coverage; EA1/EA2 lifecycle and adapter tests; F1.1 Action 15 decision; F2 full evidence; final targeted Local/Regret/lifecycle/atomic nodes.
