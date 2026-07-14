# Cascade removal equivalence

The focused suite retains an exact test-only copy of the pre-Stage-2D.0 Cascade algorithm as an equivalence oracle. For the same coordinated State, configuration, removal strength, and seeded recording RNG, it compares:

- RNG method/argument sequence;
- final removed customer IDs;
- ordered bundle customer IDs;
- preserved current implementation/dependency order;
- van routes and drone sorties;
- `unassigned` and `service_mode`;
- complete metadata-independent `TVDState.cache_signature()`;
- objective value.

All comparisons pass. The only intended delta is that raw `List[List[int]]` metadata is replaced by structured immutable snapshots plus lifecycle metadata. No random call is added, no removal call is reordered, and no customer or partition behavior is changed.
