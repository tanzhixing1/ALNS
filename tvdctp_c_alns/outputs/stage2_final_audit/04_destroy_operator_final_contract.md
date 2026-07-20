# Four Destroy Operators — Final Contract

All four paper-mode destroys are frozen. Every destroy operates on a copy, clears stale Cascade metadata/context, and attaches a fresh immutable `RemovalStructuralContext` to the disposable destroyed candidate.

## Random Removal

- Eligible domain: sorted unique currently van- or drone-served customer IDs.
- Requested quantity: `max(1, round(total customers × customer_removal_ratio))`, capped at eligible size.
- RNG: exactly one `rng.choice(..., replace=False)` when the domain is non-empty; zero otherwise.
- Selection/return order: the Generator's returned order is retained for selection and deletion trace; actual collateral unassignment is separately recorded.
- Classification: **PAPER PARTIAL + APPROVED ENGINEERING DECISION**; exact NumPy call semantics are not a paper rule.

## Greedy Removal

- For each served customer, remove it on an isolated trial, clear its trial unassigned marker, and compute `base_cost - trial_cost`.
- Select the largest marginal contributions; Python tuple reverse ordering gives a stable customer-ID tie decision.
- No RNG call is consumed. Trial sequence/ranking and ordinary context are regression-frozen.
- Classification: **PAPER PARTIAL + APPROVED ENGINEERING DECISION**.

## Related Removal

- Choose one seed uniformly from the sorted served domain.
- Rank all served customers by ground distance from that seed; stable sorted-domain order resolves equal distances.
- Take the configured removal count. The only operator RNG call is the seed choice.
- Classification: **PAPER PARTIAL + APPROVED ENGINEERING DECISION**; the exact relatedness metric/order is not uniquely fixed by the paper evidence.

## Native Cascade-aware Removal

- Eligible seed domain and count policy are unchanged from the approved pre-F baseline. One no-replacement choice is made when eligible; seed return order is retained.
- The immutable pre-destroy `StructuralProjection` creates a customer-only graph using the closed predicate inventory:
  - `NCD-A-SAME-SUBROUTE`: symmetric links among customer endpoints on the same drone sub-route.
  - `NCD-B-LAUNCH-RECOVERY`: directed order only where both coordination endpoints are customers.
- Ordered worklist reachability computes the exact fixed point `R*`, with no depth, feasibility, probability, top-K, or beam cutoff. This recursive closure/final set/simultaneous-removal obligation is **PAPER EXPLICIT**.
- The induced `R*` graph is partitioned into disjoint weak components. Component ordering follows earliest closure discovery; `dependency_order` is ascending customer ID. Both are deterministic **APPROVED ENGINEERING DECISIONS**, not paper-explicit rules.
- Path B safety performs removal on an isolated working copy, captures snapshots before mutation, and requires actual newly-unassigned membership to equal `R*`. Any out-of-R* collateral effect fails atomically and leaves the caller unchanged.
- Native bundles are installed directly; the ordinary adapter call count is zero.

Limit: the graph intentionally does not invent customer edges for broad truck/warehouse, broad same-van/route/container, or carrier/resource relationships lacking two explicit customer endpoints. This is a **KNOWN CONSERVATIVE REPRESENTATION GAP**. The baseline does not claim all truck-level dependencies or a word-for-word complete paper realization.

Evidence: EA1 ordinary equivalence/lifecycle; F0 paper matrix; F1 predicate, closure, partition, seed, membership and atomic tests; F2 two-run matrix and ordinary/native attribution; final 31-node targeted gate.
