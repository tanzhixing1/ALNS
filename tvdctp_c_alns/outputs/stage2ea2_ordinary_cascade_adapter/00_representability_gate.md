# Stage 2E-A.2 representability gate

## Baseline note

- Required production baseline: `901ee48da0e1d83fb05dcfb9903c91566e3c69fc`.
- Actual Git starting point: `8331bb87f9c32c4360bcd7f873273c91f72e2827`.
- The only difference is the user commit `论文本体来了`, which adds
  `tvdctp_c_alns/1-s2.0-S136655452600373X-main.pdf`.
- Production source, tests, tracked reports and executable behavior are
  byte-for-byte unchanged from `901ee48`; the PDF is out of scope and will not
  be modified, staged by A.2, deleted or recommitted.

## Static and dynamic evidence

`RemovalStructuralContext` retains the complete immutable pre/post structural
projections plus authoritative mutation facts. The pre projection contains
ordered van routes and positions, ordered sortie facts, launch/recovery links,
carrier-transfer facts, stable direct coordination edges, customer service
facts, container decisions and warehouse/carrier maps. These facts cover every
field consumed by the existing `CascadeBundleSnapshot` and existing Ω(B).

Dynamic checks used the committed coordinated Stage 2D fixture before any A.2
production edit:

- singleton van removal `R={10}` retained position `van_0:3` and exact
  predecessor/successor customers `{9,11}`;
- contiguous van removal `R={9,10}` retained structural order `9→10` and exact
  external boundaries `{5,11}`;
- removing one customer from original sortie `[7,9]` produced actual
  `R={7,9}` and retained the complete original sortie and its anchor facts;
- removing launch anchor `5` produced actual `R={5,7}`, proving a direct
  anchor-to-sortie dependency without same-route inference;
- a two-sortie carrier chain retained ordered facts for the same physical
  drone, a real `van_0→van_1` recovery transfer, and the immediately following
  launch from `van_1`.

| Structure | Raw facts available | Existing snapshot representable | Existing Ω(B) consumable | Result |
| --- | ---: | ---: | ---: | --- |
| Singleton van | YES | YES | YES | PASS |
| Contiguous van block | YES | YES | YES | PASS |
| Full removed sortie | YES | YES | YES | PASS |
| Partial actual-R sortie | N/A under current mutation | YES, validation rejects partial membership | YES | PASS |
| Launch/recovery anchor | YES | YES | YES | PASS |
| Carrier-transfer chain | YES | YES | YES | PASS |
| Explicit coordination edge | YES | YES | YES | PASS |

## Edge discipline

- Van edges require adjacent R customers in the same original route.
- Sortie edges require adjacent R customers in the same original sortie.
- Anchor edges require an R customer to equal the sortie's explicit launch or
  recovery node and another R customer to belong to that sortie.
- Carrier edges require adjacent source sorties for the same physical drone,
  a real previous recovery carrier transition, and equality between that
  recovery carrier and the next launch carrier. Same drone ID alone is never
  sufficient.
- Explicit coordination edges are accepted only by stable pre-projection
  identity and direct customer endpoints. Proximity, route, warehouse,
  container, drone identity or customer-ID similarity never creates an edge.

`_remove_customer` removes the complete sortie whenever any sortie customer or
customer anchor is removed and marks every sortie customer unassigned.
Therefore:

`PARTIAL-SORTIE ACTUAL-R CASE NOT PRODUCED BY CURRENT DESTROY SEMANTICS`.

No Ω(B), checker, objective or destroy algorithm change is necessary for
representability.

## Decision

REPRESENTABILITY PASS
