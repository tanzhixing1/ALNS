# Stage 2F.1 Pre-implementation Baseline

Baseline HEAD: `760e3bc445b04fd2673c81774c90d30422f890df`.

The four Stage 2F.0 canonical-feasible fixtures were reused without modifying the Stage 2F.0 evidence. Each case was observed twice. The source business fingerprint was `b9f9ede9f8a413b4e214e3afa4d98e9111c0e79b6945e9e57e9bc64a0a5048dc` in all runs.

## Frozen seed policy

- Eligible domain: sorted union of currently van-served and drone-served customer IDs (`_served_customers`).
- Van-served customers: included.
- Drone-served customers: included.
- Customer-valued launch/recovery anchors: included when currently served by the van/drone business state.
- Already unassigned customers: excluded because they are absent from both served lists.
- Warehouse/depot and non-customer anchors: excluded from the served customer union.
- Requested count: `min(max(1, round(len(data.customers) * ratio)), len(eligible))`.
- RNG: exactly one `rng.choice(sorted_eligible, size=count, replace=False)` when eligible is non-empty; zero calls otherwise.
- Seed order: the order returned by `rng.choice`.

Classification: **PAPER UNSPECIFIED; CURRENT DETERMINISTIC ENGINEERING POLICY**.

## Observed cases

| Fixture | Runs | Count | Eligible input | Seed order | Current dependency expansion | Current closure/order | Bundles | dependency_order | Newly unassigned | Native adapter calls | RNG trace | Destroyed fingerprint |
|---|---:|---:|---|---|---|---|---|---|---|---:|---|---|
| single_cross_van_chain | 2 | 1 | 5,6,7,8,9,10,11,12 | 8 | 8→6 | membership 6,8; removal 8,6 | [6,8] | [6,8] | 6,8 | 0 | one choice; replace=False | `e877c3666cacb4ff1af0f567ec23f89eba89a748c168b1c0c0e8504f8b00d12c` |
| same_sortie_duplicate_membership | 2 | 1 | 5,6,7,8,9,10,11,12 | 5 | 5→7 | membership 5,7; removal 5,7 | [5,7] | [5,7] | 5,7 | 0 | one choice; replace=False | `dc758e7946c8938fb6031fc95af3c0537129893d767e23d6306a6307572e8b4d` |
| two_dependency_chains_two_bundles | 2 | 2 | 5,6,7,8,9,10,11,12 | 8,7 | 8→6; 7→5 | membership 5,6,7,8; removal 5,6,7,8 | [5,7]; [6,8] | [5,7]; [6,8] | 5,6,7,8 | 0 | one choice; replace=False | `f6b8b4e95962feba350fcfba08e04922575dfba3beea3389fbe42cc1420bd37e` |
| two_seed_two_chain_order | 2 | 2 | 5,6,7,8,9,10,11,12 | 8,5 | 8→6; 5→7 | membership 5,6,7,8; removal 5,6,7,8 | [5,7]; [6,8] | [5,7]; [6,8] | 5,6,7,8 | 0 | one choice; replace=False | `f6b8b4e95962feba350fcfba08e04922575dfba3beea3389fbe42cc1420bd37e` |

All twice-run observable fields required by Stage 2F.0 were equal within each pair. The old deletion traversal used Python-set order; this is recorded as baseline behavior, not retained as a contract.
