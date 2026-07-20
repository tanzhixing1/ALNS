# Stage 2F.1 Gate Decision

Implementation commit: `9488139b8920640b47a8a901e32129df0076200f`.

| Gate | Result | Evidence |
|---|---|---|
| Baseline correct | PASS | Baseline `760e3bc445b04fd2673c81774c90d30422f890df`; tracked/staged clean before work |
| Predicate inventory closed | PASS | `01_dependency_predicate_inventory.md` |
| No generic catch-all predicate | PASS | Exact NCD-A/NCD-B allowlist only |
| Every implemented predicate has field evidence | PASS | `DroneSortieFact` and exact `CoordinationEdgeFact` fields |
| Every predicate has positive test | PASS | New focused predicate tests |
| Every predicate has negative test | PASS | Unrelated/non-customer/direction tests |
| Boundary tests added where applicable | PASS | Anchor, resource, repeated occurrence tests |
| Multiple-occurrence rank resolution deterministic | PASS | Minimum pre-destroy occurrence rank fixture |
| Represented dependencies fully implemented | PASS | NCD-A/NCD-B implemented |
| Known unrepresented gaps recorded | PASS | `02_representation_gap_register.md` |
| Known gaps not falsely claimed covered | PASS | Truck/van/carrier gaps explicitly retained |
| Current seed eligibility audited | PASS | `00_preimplementation_baseline.md` |
| Seed eligibility preserved or explicitly approved | PASS | Exact sorted served domain retained |
| Seed policy preserved | PASS | Count, one choice, no replacement, returned order |
| RNG call count preserved | PASS | One call when eligible; zero otherwise |
| Graph built pre-destroy | PASS | Immutable projection captured before mutation |
| Graph nodes are customers only | PASS | Explicit `data.customers` allowlist |
| Non-customer structures do not enlarge R* | PASS | Resource/warehouse exclusion tests |
| Ordered closure exact | PASS | Cursor worklist; membership-only set |
| Multi-hop closure correct | PASS | Focused chain/merge tests |
| Cycles terminate | PASS | Cycle/self-loop/duplicate tests |
| R* equals graph reachability | PASS | Focused exact reachability assertions |
| Weak components correct | PASS | Directed weak-connectivity and component tests |
| Bundle union equals R* | PASS | Runtime assertions and all fixture traces |
| Bundles pairwise disjoint | PASS | Runtime assertions and tests |
| Bundle order deterministic | PASS | Earliest closure discovery member |
| dependency_order unchanged and deterministic | PASS | Ascending IDs; frozen repair semantics string |
| Snapshots captured pre-removal | PASS | Snapshot creation precedes `_remove_customers` |
| Atomic co-removal safety passes | PASS | Path B exact-membership validation |
| Caller input State unchanged on failure | PASS | Poisoned-removal atomic failure test |
| Removal newly-unassigned membership equals R* | PASS | Runtime fail-fast equality and four double-runs |
| Failure paths atomic | PASS | No returned candidate/context/fallback |
| Native bypasses adapter | PASS | Stage 2E-A.2 direct test |
| Ordinary paths unchanged | PASS | No ordinary production diff; selected isolation tests |
| Cascade repair untouched | PASS | Source diff absent; 33 Stage 2D.1 tests pass |
| Objective/checker untouched | PASS | Source diff absent |
| Paper registry untouched | PASS | Action 15 direct test |
| Focused tests pass | PASS | `81 passed in 23.71s` |
| Production diff within allowed scope | PASS | Only `operators.py` production change |
| Stage 2F.2 not performed | PASS | Held |
| Stage 2G not performed | PASS | Held |

## Git closeout

```text
baseline HEAD=760e3bc445b04fd2673c81774c90d30422f890df
STAGE_2F1_COMMIT=9488139b8920640b47a8a901e32129df0076200f
tracked diff=0
staged diff=0
```

Only the designated output directories remain untracked.

## Decision

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

This decision does not claim full paper verification, complete truck-level dependencies, or a frozen final C-ALNS paper baseline.
