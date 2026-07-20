# Native Bundle Contract Validation

Decision input: current Action 15 in the frozen paper and extended fixtures.

| Contract item | Required | Current evidence | PASS/FAIL | Source |
|---|---|---|---|---|
| bundle `customer_ids` non-empty | yes | sizes paper `3,5`; extended `5,3` | PASS | Stage 2D bundle contract; trace JSON |
| no duplicate within bundle | yes | each tuple has unique IDs | PASS | Stage 2D strict validator |
| bundles pairwise disjoint | yes | intersections empty in both modes | PASS | Stage 2F.1 MED-4; dedicated test |
| bundle union equals R* | yes | union is `{5,6,7,8,9,10,11,14}` | PASS | Stage 2F.1 MED-4/Path B |
| `dependency_order` matches membership | yes | exact permutation; equal ascending tuple | PASS | Stage 2D validator; Stage 2F.1 MED-5 |
| `dependency_order` stable ascending | engineering rule | paper `[7,9,10]`, `[5,6,8,11,14]`; extended reverse component order with same within-order | PASS | Stage 2F.1 MED-5 |
| snapshot is pre-destroy | yes | `captured_before_removal=True`; source fingerprint equals Action-15 input fingerprint | PASS | Stage 2D snapshot contract |
| snapshot customer IDs equal component | yes | exact for every bundle | PASS | bundle JSON; strict validator |
| route facts complete | when associated | exact van ID, absolute position and bounded pre-route slice | PASS | trace JSON; Stage 2D snapshot tests |
| sortie facts complete | when associated | exact source index, drone, customers, launch, recovery | PASS | trace JSON |
| launch/recovery complete | when associated | node, van, position and same-van flag reproduced | PASS | trace JSON |
| carrier facts complete | when associated | initial/launch/recovery van and transfer flag reproduced | PASS | trace JSON |
| truck/warehouse facts complete | yes | selected transshipment 3 and container 0 decision retained | PASS | trace JSON |
| affected scope consistent | yes | strict `_validated_cascade_bundles` passes before enumeration | PASS | production boundary reached |
| context lifecycle correct | yes | present after destroy, detached before candidate work, absent on return/final best | PASS | probe; dedicated test |
| Native bypasses ordinary adapter | yes | source operator is `cascade_aware_removal`; no adapted contract fields | PASS | Stage 2E-A.2 test; trace |
| actual newly-unassigned equals R* | yes | exact in both modes | PASS | Path B runtime check; trace |

The baseline four-bundle layouts are not a counterexample: they overlap at customers 5 and 9 and each snapshot can include a sortie customer outside the nominal bundle. That is the defect Stage 2F.1 was specifically required to correct.

```text
NATIVE BUNDLE INPUT CONTRACT PASS
```

