# Native Cascade Four-Pair Attribution

## Stage 2E-A.2 matrix fixture

Seed 29 selects isolated customer 12, so the induced customer graph has no edge. Each Native destroy performs one production graph build, one RNG seed draw, zero ordinary-adapter calls, exact Path B membership, and returns a clean State after repair.

| ID | Pair | Seed | Edges / hits | Discovery / R* | Bundle | Category | Checker / objective calls | Change |
|---:|---|---|---|---|---|---:|---:|---|
| 12 | Cascade + Global | `[12]` | none | `[12]` / `[12]` | `[12]` | B | 1 / 0 | exact baseline |
| 13 | Cascade + Local | `[12]` | none | `[12]` / `[12]` | `[12]` | B | 1 / 0 | exact baseline |
| 14 | Cascade + Regret-2 | `[12]` | none | `[12]` / `[12]` | `[12]` | A | 2 / 76 | exact baseline |
| 15 | Cascade + Cascade | `[12]` | none | `[12]` / `[12]` | `[12]` | A | 7 / 4 | exact baseline |

## Non-trivial fixed-point fixtures

The Stage 2F.0/2F.1 probe was repeated twice per case:

- `[8]` → edge `8→6`, R* `[6,8]`, bundle `[6,8]`;
- `[5]` → edge `5→7`, R* `[5,7]`, bundle `[5,7]`;
- `[8,7]` → R* `[5,6,7,8]`, bundles `[6,8] | [5,7]`;
- `[8,5]` → same R*, stable discovery `[8,5,6,7]`, same two bundles.

All use only NCD-A/NCD-B, weak components, stable ascending Native `dependency_order`, exact `newly_unassigned == R*`, pre-removal snapshots, and no RNG after the one seed draw. Every double-run pair matched.

## Approved Action 15 flow

- Paper iteration 7: seed `[7,14]`; R* `[5,6,7,8,9,10,11,14]`; bundles `[7,9,10] | [5,6,8,11,14]`.
- Extended iteration 8: seed `[11,7]`; same R*; bundles `[5,6,8,11,14] | [7,9,10]`.
- Each mode: one raw snapshot, one checker rejection, zero objective scoring, empty-Ω(B) rollback, no context leak, unchanged final best.
- Whole solver totals: paper checker/objective `910/653`; extended `885/608`.

Unexplained Native changes: 0. Full matrix traces are in `04a_native_four_pair_trace.csv`; Action 15 raw traces are `action15_paper.json` and `action15_extended.json`.

```text
NATIVE FOUR-PAIR ATTRIBUTION PASS
ACTION-15 APPROVED CONTROL FLOW PASS
```
