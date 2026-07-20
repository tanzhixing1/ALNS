# Action 15 Interface Trace

The trace replays the exact Stage 2E.1 10-customer, 12-iteration, seed-42 fixture with ALNS seed 29 in detached baseline (`760e3bc...`) and current (`9488139b...`) worktrees. The probe wraps existing boundaries and invokes every wrapped production function exactly once.

## Paper mode

| Fact | Baseline | Current |
|---|---|---|
| iteration / action | 7 / 15 | 7 / 15 |
| Native seeds | `[7, 14]` | `[7, 14]` |
| dependency model | legacy per-customer sortie query | pre-destroy ranked NCD-A/NCD-B graph |
| closure trace | `14->5, 14->8, 7->9, 5->6, 5->11, 9->10` | `7->9, 14->5, 14->8, 9->10, 5->6, 5->11` |
| R* | `[5,6,7,8,9,10,11,14]` | same |
| deletion attempt order | `[5,6,7,8,9,10,11,14]` | `[7,14,9,5,8,10,6,11]` |
| actual newly unassigned | `[5,6,7,8,9,10,11,14]` | same membership |
| bundles | `[7,9]`, `[9,10]`, `[5,8,14]`, `[5,6,11]` | `[7,9,10]`, `[5,6,8,11,14]` |
| dependency order | equal to each listed membership | equal to each listed membership, ascending |
| Path B membership check | absent | `actual newly-unassigned == R*` PASS |
| Cascade contract validation | FAIL: overlaps at 9 and 5; sortie membership mismatch | PASS |
| processed bundle | none | `[7,9,10]` |
| raw candidates | 0 | 1 snapshot; 0 van-block; 0 drone-bundle |
| snapshot candidate | none | route `van_0=[3,9,12,3]`; sorties restore `7` and `10` from/to node 9 |
| candidate unassigned | none | `[5,6,8,11,14]`, exactly the later bundle |
| checker result | not reached | infeasible |
| retained violations | none | high-floor customers 8, 11 and 14 must be served by drone |
| objective scoring | 0 | 0 |
| strategy result | contract failure | empty feasible strategy set |
| repair return | atomic destroyed-State copy | atomic destroyed-State copy |
| context after return | absent | absent |

The current first bundle snapshot records customer 7 as drone, 9 as van at `van_0` position 1, and 10 as drone. It records two same-van sorties (`7` and `10`) launched/recovered at customer 9, both carrier links, bounded route segment `[3,9,5]`, container 0 and selected transshipment 3. The restored raw candidate reproduces those facts.

## Extended mode

| Fact | Baseline | Current |
|---|---|---|
| iteration / action | 8 / 15 | 8 / 15 |
| Native seeds | `[11, 7]` | `[11, 7]` |
| closure trace | `11->5, 11->6, 7->9, 5->8, 5->14, 9->10` | `11->5, 11->6, 7->9, 5->14, 5->8, 9->10` |
| R* | `[5,6,7,8,9,10,11,14]` | same |
| deletion attempt order | `[5,6,7,8,9,10,11,14]` | `[11,7,5,6,9,14,8,10]` |
| actual newly unassigned | `[5,6,7,8,9,10,11,14]` | same membership |
| bundles | `[9,10]`, `[7,9]`, `[5,6,11]`, `[5,8,14]` | `[5,6,8,11,14]`, `[7,9,10]` |
| Cascade contract validation | FAIL: overlaps and sortie membership mismatch | PASS |
| processed bundle | none | `[5,6,8,11,14]` |
| raw candidates | 0 | 1 snapshot; 0 van-block; 0 drone-bundle |
| snapshot candidate | none | route `van_0=[3,12,5,3]`; restores sorties `[6,11]` and `[14,8]` at node 5 |
| candidate unassigned | none | `[7,9,10]`, exactly the later bundle |
| checker result | not reached | infeasible |
| retained violations | none | high-floor customer 10 must be served by drone |
| objective scoring | 0 | 0 |
| strategy result | contract failure | empty feasible strategy set |
| repair return / context | atomic destroyed State / absent | atomic destroyed State / absent |

The current first bundle snapshot records 5 as van at `van_0` position 2 and 6/8/11/14 as drone customers. Its two same-van sortie, anchor, carrier, bounded route segment `[9,5,12]`, container and warehouse facts all match the pre-destroy State and are reproduced by the snapshot candidate.

## Isolation

- Repair RNG fingerprints are identical before/after in all four cases.
- Current repair adds exactly one checker call and zero objective calls in both modes.
- Action 15 is rejected and not accepted in both versions/modes.
- Frozen action sequences, acceptance, objective totals, final objectives and final best-State fingerprints remain unchanged.
- Raw evidence: the four `*_action15.json` files; row summary: `01a_action15_interface_trace.csv`.

