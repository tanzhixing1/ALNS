# Extended Registry Cartesian Audit

Audit source: live production APIs `build_action_registry`, `DESTROY_OPERATORS`, and `REPAIR_OPERATORS` at HEAD `760e3bc445b04fd2673c81774c90d30422f890df`.

The solver source was independently inspected. Its actual roulette inputs are `list(action_registry.destroy_names)` and `list(action_registry.repair_names)`, followed by two separate `_roulette_choice` calls.

## Paper registry

- destroy names (4): `random_customer_removal`, `greedy_removal`, `related_customer_removal`, `cascade_aware_removal`
- repair names (4): `best_mode_repair`, `greedy_van_repair`, `regret_repair`, `cascade_repair`
- action count: 16
- IDs: exactly 0 through 15
- fingerprint: `08a24ddd74d3d05577f7673df93d8f302b78f3f65d806c91d19e5a67c55d71a1`
- ordered action specs: rows 0 through 15 of `00_extended_actions.csv`

## Extended registry

- destroy names (7): `random_customer_removal`, `greedy_removal`, `related_customer_removal`, `route_segment_removal`, `drone_task_removal`, `cascade_aware_removal`, `switch_transshipment_operator`
- repair names (5): `greedy_van_repair`, `greedy_drone_repair`, `best_mode_repair`, `regret_repair`, `cascade_repair`
- action count: 35
- fingerprint: `588c3c20cc1b34c66bb90f4e6e3296af5397f1ad4ba671b07d59f1f15a446514`
- ordered action specs: all rows of `00_extended_actions.csv`

| Check | Value |
| --- | ---: |
| extended destroy count | 7 |
| extended repair count | 5 |
| destroy count x repair count | 35 |
| approved action count | 35 |
| missing cross pairs | 0 |
| extra pairs | 0 |
| duplicate pairs | 0 |
| duplicate IDs | 0 |
| ID holes | 0 |

Paper IDs 0 through 15 have identical `(action_id, destroy, repair, display_name)` semantics in extended mode. Extended-only IDs start at 16 and continue through 34 without holes.

**EXTENDED INDEPENDENT-ROULETTE CONTRACT PASS**
