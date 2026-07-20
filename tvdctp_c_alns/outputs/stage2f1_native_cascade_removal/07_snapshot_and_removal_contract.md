# Snapshot and Removal Contract

- Bundle snapshots are constructed only after the complete graph, closure and weak-component partition exist, and before `_remove_customers` is called.
- Snapshot schema is unchanged.
- Context schema is unchanged.
- Snapshot `customer_ids` equals the component's ascending customer IDs.
- `dependency_order` equals the same ascending tuple; its business meaning remains the frozen repair-compatible “current implementation order; Paper unspecified”.
- Route, sortie, launch/recovery, carrier, truck and warehouse facts continue to be captured by the existing snapshot builder.
- Removal attempts follow `R_star_discovery_order`, never Python-set traversal.
- `actual_unassignment_order` may reflect authoritative sortie side effects, but its new membership is required to equal `R*`.

Post-implementation double-run business fingerprints:

| Fixture | Fingerprint | Explanation |
|---|---|---|
| single_cross_van_chain | `e877c3666cacb4ff1af0f567ec23f89eba89a748c168b1c0c0e8504f8b00d12c` | Single chain; unchanged business order |
| same_sortie_duplicate_membership | `dc758e7946c8938fb6031fc95af3c0537129893d767e23d6306a6307572e8b4d` | Single chain; unchanged business order |
| two_dependency_chains_two_bundles | `634367660e6fbf781c1405217da571107c1526c1e1b226bcabedb9d0213ebdba` | Stable discovery-order removal replaces set traversal |
| two_seed_two_chain_order | `11b149d1d3a3f9a6d4952db070b2a6c56d7fda25434b4c26c6b948b34d0666a9` | Seed order drives stable discovery/removal order |

Every double-run pair was identical and every resulting Native contract passed `cascade_metadata_is_current`.
