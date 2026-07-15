# Three pairs remain blocked

Stage 2E-A.1 deliberately does not adapt ordinary destroy contexts to Cascade
repair bundles.

| Planned label (not current ID) | Pair | Result |
| ---: | --- | --- |
| 3 | Random + Cascade | explicit failure: missing Cascade contract/bundles |
| 7 | Greedy + Cascade | explicit failure: missing Cascade contract/bundles |
| 11 | Related + Cascade | explicit failure: missing Cascade contract/bundles |

Each ordinary destroy now has a valid repair-agnostic raw context, but the
existing Cascade validator still accepts only source
`cascade_aware_removal` with the unchanged Stage 2D contract. The lifecycle
wrapper consumes the raw context and does not synthesize metadata.

Post-change target matrix: **13 contract-compatible, 3 contract-incompatible,
crashed/polluted 0**. No planned label is treated as a current production
registry action ID.

`DEFER TO STAGE 2E-A.2`: ordinary bundle grouping, dependency order, adapter
validation and the three unlocks.
