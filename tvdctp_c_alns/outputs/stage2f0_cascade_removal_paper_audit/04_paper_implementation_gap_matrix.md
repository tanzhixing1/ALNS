# Paper–Implementation Gap Matrix

The comparison subject is paper Cascade-aware Removal versus the production **Native** `cascade_aware_removal` path. Infrastructure is not treated as a paper algorithm merely because it carries Cascade data.

| Topic | Classification | Paper contract | Current Native behavior | Consequence |
|---|---|---|---|---|
| seed selection | PARTIALLY ALIGNED | `R^(0)` comes from a preceding removal strategy; exact standalone generator is partial. | Native independently samples a multi-customer set uniformly without replacement from sorted van+drone served customers. | Random sampling is one plausible engineering realization, but provenance is not “any preceding strategy,” and eligible-domain wording is ambiguous. Preserve as MED unless Stage 2F.1 explicitly resolves it. |
| removal quantity | PARTIALLY ALIGNED | A predefined proportion/`k` controls the initial removal set; closure may expand it. | `round(total customers * ratio)`, minimum 1, capped by served count. | Shape aligns; rounding/minimum are engineering choices. |
| dependency relation | PARTIALLY ALIGNED + NOT IMPLEMENTED | Same drone sub-route and effects of associated truck/van decisions are in `D_i`. | Detects only a sortie containing the node, then adds sortie customers and non-warehouse anchors. | Same-sortie core is represented; general truck/van/coordination dependencies are absent. This is the primary confirmed paper gap. |
| dependency direction | PARTIALLY ALIGNED | Impact propagation is described, but exact directed graph is partial. | Relationship within a matching sortie is effectively symmetric; no direction metadata drives closure. | Cannot claim paper direction is implemented; Stage 2F.1 needs an explicit minimal direction interpretation or documented symmetric component rule. |
| recursive expansion | ALIGNED | Formula (93) and Algorithm 1 require recursive union. | Repeats until no dependency adds a customer. | Fixed-point control structure aligns. |
| closure termination | ALIGNED | Stop at `R^(t+1)=R^(t)`. | `changed` loop stops when every returned dependency is already in the set. | Aligned for the implemented static predicate. |
| final `R*` | PARTIALLY ALIGNED | Fixed point over the paper dependency relation. | Fixed point over `_cascade_dependencies`. | Control semantics align, but the resulting customer set may be smaller because `D_i` is incomplete. |
| related route | NOT IMPLEMENTED | Associated truck/van route decisions and vehicle route segments are affected structures. | Closure does not discover customers through truck/van route relationships. Snapshot code records route segments only after bundle membership is already chosen. | Structural snapshot coverage does not repair missing customer dependency discovery. |
| related sub-route | PARTIALLY ALIGNED | Same/associated drone sub-routes participate and are removed with `R*`. | Same sortie customers and customer-valued anchors are included; matching sortie is removed if any member is removed. | Basic sortie coupling aligns; chained sorties/carrier transfers and broader associated sub-routes are absent from closure. |
| duplicate handling | PARTIALLY ALIGNED | Set union deduplicates customer membership; bundle output is a partition. | `removal` is a set and unassigned is deduplicated. Per-sortie bundle construction can emit overlap if structures share a customer; validator later rejects it. | Customer `R*` dedupe aligns, but Native bundle construction is not guaranteed to be a partition for every representable structure. |
| multiple-chain merging | ALIGNED for customer union | All reachable chains from all seeds union into `R*`. | All discovered dependencies are unioned in one set. | Customer merge aligns for current predicate; trace retains only newly added edges. |
| bundle partition | PARTIALLY ALIGNED | Partition `R*` according to structural dependency relationships. | One bundle per sortie intersection, then singleton leftovers. No general dependency-component computation; possible overlaps are not subtracted. | Needs a complete, disjoint dependency-grounded partition in Stage 2F.1. Exact component rule is a MED because the paper is partial. |
| dependency order | PAPER UNSPECIFIED + ENGINEERING INTERPRETATION | No within-bundle customer order. | `dependency_order` equals sorted `customer_ids`. | Retain or change only as an explicitly labeled deterministic engineering decision; do not call it paper alignment. |
| tie-breaking | PAPER UNSPECIFIED | No exact ties specified. | Customer sorting, State sortie order, set iteration, and stable IDs determine outcomes. | Freeze deterministic rules in tests; no paper claim. |
| RNG call logic | PARTIALLY ALIGNED + PAPER UNSPECIFIED | Initial removal can be random; closure RNG is not specified. | One `rng.choice` for Native `R^(0)`; no closure/partition/snapshot RNG. | Reasonable and deterministic, but exact API/distribution is not a paper mandate. |
| RNG call order | PAPER UNSPECIFIED + ENGINEERING INTERPRETATION | Not given. | Solver consumes destroy/repair selection RNG first; Native then consumes one choice; Cascade repair consumes none. | Preserve baseline call order unless a paper-backed seed change requires an explicitly tested difference. |
| removal execution order | PAPER UNSPECIFIED + ENGINEERING INTERPRETATION | Removal is simultaneous. | Iterates the Python set and records that deletion order; `_remove_customer` may unassign sortie peers before their own deletion attempt. | Business set can be correct while order differs. Use an explicit stable worklist in Stage 2F.1 if order is made contractual. |
| snapshot timing | ENGINEERING INTERPRETATION | Associated structures are removed together; storage mechanism unstated. | All bundle structural snapshots are captured before destructive mutation. | Supports simultaneous semantics and does not alter seed/closure/RNG; retain. |
| context creation timing | ENGINEERING INTERPRETATION | No context object in paper. | Context is finalized after removal from authoritative pre/post projections and then attached to the disposable candidate. | Does not select customers or consume RNG; retain. |

## Confirmed algorithm gaps

1. `_cascade_dependencies` does not implement the paper-described truck/van/coordination dependency scope beyond same-sortie membership and anchors.
2. Native bundle creation is not based on a complete structural dependency graph and is not guaranteed by construction to be a disjoint partition.
3. The final customer set has the correct fixed-point **shape**, but cannot be certified as the paper `R*` until the dependency predicate is corrected.

No evidence supports labeling the current `dependency_order`, set traversal order, or exact NumPy RNG sequence as a paper rule.

## Infrastructure separation

- `RemovalStructuralContext`: records immutable pre/post facts; it does not change Native seeds, closure, `R*`, or RNG.
- Ordinary adapter: invoked only when Cascade repair receives Random/Greedy/Related context; focused test confirms Native bypass.
- Lifecycle cleanup: consumes/discards context and prevents persistence in current/best; it does not expand `R*`.
- Action registry: keeps paper mode at 4×4 and Native Cascade + Cascade at action 15; it does not change operator internals.

