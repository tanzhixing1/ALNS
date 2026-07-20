# Stage 2F.1 Native Cascade-aware Removal Correction

## Git

- Baseline HEAD: `760e3bc445b04fd2673c81774c90d30422f890df`
- Implementation commit: `9488139b8920640b47a8a901e32129df0076200f`
- Tracked diff: clean
- Staged diff: clean

## Predicate inventory

- Implemented: `NCD-A-SAME-SUBROUTE`, `NCD-B-LAUNCH-RECOVERY`.
- Rejected: carrier/resource predicates without two explicit customer endpoints.
- Generic catch-all: absent.
- Represented dependency gaps: corrected for the closed inventory.
- Known conservative gaps: truck/warehouse downstream, general van-route downstream, carrier-transfer/linked-sortie customer propagation.
- Multiple-occurrence rank: minimum lexicographic pre-destroy occurrence rank, then provenance.

## Seed

- Current eligible domain: sorted union of currently van-served and drone-served customers.
- Evidence: `_served_customers` and four Stage 2F.0 fixture double-runs.
- Eligible domain changed: no.
- Requested count: existing `max(1, round(total customers × ratio))`, capped by eligible count.
- RNG call count: one `choice` without replacement when eligible, zero otherwise.
- Seed order: exact RNG return order.

## Dependency graph

- Source: immutable pre-destroy `StructuralProjection`.
- Node type: customer IDs only.
- Symmetric predicate: same drone sub-route.
- Directed predicate: exact customer-to-customer launch/recovery order.
- Non-customer scope: snapshots only; never graph/R* membership.

## Closure

- Worklist: seed order followed by newly discovered targets.
- Neighbor order: structural rank, target customer, predicate ID, provenance.
- Fixed point: exact graph reachability, no depth/feasibility/probability cutoff.
- Cycles: membership tracking termination.
- R* membership: all customers reachable from all seeds.
- Discovery order: stable ordered worklist.

## Bundles

- Partition: weak components of the graph induced by R*.
- Canonical fixture component count: one or two depending on selected seeds.
- Exact union: pass.
- Overlaps: none.
- Bundle order: earliest member in closure discovery order.
- `dependency_order`: ascending customer ID; paper-unspecified deterministic engineering order.

## Safety

- Safety path: Path B.
- Snapshots captured before mutation: yes.
- Authoritative static preflight available: no exact independent predictor.
- Isolated working copy: yes.
- Out-of-R* side effects: fail fast with `ATOMIC CO-REMOVAL CONTRACT VIOLATION`.
- Caller State unchanged on failure: verified.
- Failure atomicity: verified; no partial candidate/context/fallback.
- Actual newly-unassigned equals R*: verified on every successful return.

## Isolation

- Ordinary destroys changed: no.
- Ordinary adapter changed: no.
- Cascade repair changed: no.
- Other repairs changed: no.
- Objective/checker changed: no.
- State changed: no.
- Paper registry changed: no; Native Cascade + Cascade remains action 15.
- Performance work performed: no.

## Tests

- Predicate tests: positive, negative and applicable boundary tests pass.
- Seed tests: eligibility, count, single RNG call and seed order pass.
- Closure tests: one-hop, multi-hop, cycles, self-loop, duplicate, multi-source, chains and isolated seed pass.
- Partition tests: one/multiple components, weak direction, singleton, exact union/disjoint/order pass.
- Atomic removal tests: exact membership and injected failure atomicity pass.
- Boundary tests: Native adapter bypass, context lifecycle, repair isolation and action ID pass.
- Focused result: `81 passed in 23.71s`.
- Full pytest suite: not run because the Stage 2F.1 instruction explicitly holds the full non-medium/medium suite and full 16-pair matrix for Stage 2F.2.

## Stage boundary

- Stage 2F.2 performed: no.
- Stage 2G performed: no.

## Commit

```text
STAGE_2F1_COMMIT=9488139b8920640b47a8a901e32129df0076200f
```

## Final decision

```text
NATIVE CASCADE CUSTOMER DEPENDENCY GRAPH CORRECTED
CASCADE FIXED-POINT R* CONTRACT PASS
NATIVE BUNDLE PARTITION CONTRACT PASS
ATOMIC REMOVAL MEMBERSHIP SAFETY PASS
PAPER-EXPLICIT RULES PRESERVED
APPROVED MINIMAL ENGINEERING DECISIONS APPLIED
KNOWN CONSERVATIVE REPRESENTATION GAPS RECORDED
STAGE 2F.1 COMPLETE
STAGE 2F.2 READY
STAGE 2G HELD
```

Not claimed: fully paper-verified Cascade-aware Removal, all truck-level dependencies implemented, or frozen final C-ALNS paper baseline.
