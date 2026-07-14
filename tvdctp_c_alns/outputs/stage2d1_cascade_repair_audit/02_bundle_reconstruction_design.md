# Bundle reconstruction design

## Paper interpretation

Cascade repair receives the ordered `CascadeBundleSnapshot` records emitted by Cascade removal. It processes each `B` separately, constructs a bundle-level feasible strategy set `Ω(B)`, evaluates each complete reconstructed candidate with `f(S ⊕π B)`, and atomically commits the selected strategy before moving to the next bundle.

Equation (95) uses `i` on its right-hand side even though the surrounding definition and Algorithm 1 operate on bundle `B`. This implementation follows the contextual bundle reading `f(S ⊕π B)`; no paper file was modified.

## Disclosed strategy family

**Implementation choice: the paper does not explicitly specify this detail.**

One candidate is a `BundleReconstructionStrategy`, never a single-customer move. The implemented family is:

1. exact joint reconstruction from the pre-removal snapshot;
2. every contiguous whole-bundle van reconstruction inside each captured affected route segment;
3. every hard-feasible whole-bundle drone reconstruction whose launch/recovery vans and anchor nodes are inside the captured affected route segments.

Every candidate restores every customer in the current bundle before validation. A candidate may use low-level route/sortie helpers, but it is retained only as a complete bundle-level resulting State and is jointly validated, jointly scored, and atomically committed.

The implementation does not generate `Ω(i1) × Ω(i2) × ... × Ω(ik)`. It also does not use top-K, a beam, candidate truncation, best-per-customer pruning, a distance threshold, a fixed recovery van, or a same-van restriction.

## Processing loop

```text
repair_base = destroyed_state.copy()
validate complete Cascade contract
working_state = repair_base.copy()

for bundle in removal-provided order:
    construct complete BundleReconstructionStrategy candidates
    reject candidates that change structures outside affected_structure_scope
    validate with canonical checker + exact allowed-unassigned wrapper
    deduplicate by complete stable identity (never by cost)
    evaluate every retained candidate with full objective
    select by (objective, stable full identity)
    if none: return repair_base as explicit atomic failure
    working_state = selected complete candidate State

validate final working_state
consume Cascade metadata
return working_state
```

## Order choices

- Bundle order: current removal-produced list order. **Implementation choice: the paper does not explicitly specify this detail.**
- `dependency_order`: used only as the stable whole-bundle sequence for candidate construction/serialization; it is not a paper customer priority and does not create a per-customer greedy loop.
- Candidate generation sequence: canonical stable identity order after identity-only deduplication.

## Full objective

Each retained candidate is passed directly to the existing `objective()` function. During intermediate bundle processing the same explicit later/external unassigned set exists for every candidate, so the canonical infeasibility penalty component is common across that bundle's alternatives; the full objective still ranks complete State candidates. No local-distance proxy is used for selection.

## Cross-van support

The snapshot strategy reconstructs the recorded launch van, recovery van, physical drone, launch/recovery nodes and positions, and carrier transfer. Whole-bundle drone enumeration retains both same-van and cross-van candidates when their two van routes and anchors are inside the affected scope. Cross-van capability is not disabled or approximated.
