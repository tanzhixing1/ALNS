# BundleReconstructionStrategy identity specification

`BundleReconstructionStrategy.stable_identity()` contains, in order:

1. bundle ID;
2. exact bundle customer membership;
3. reconstructed service mode for every bundle customer;
4. complete resulting route for every affected van-route segment ID;
5. affected drone sub-route identities: physical drone, launch van/node/position, ordered customers, recovery van/node/position;
6. launch/recovery reconstruction;
7. initial/launch/recovery carrier and transfer flag;
8. affected coordination-link IDs.

The resulting State object, generator/source label, elapsed time, and objective value are deliberately excluded from identity. Objective cost is never used for deduplication: two structurally different strategies with equal costs remain in `Ω(B)`.

Identity values are tuples of deterministic scalar/tuple fields. Dict, set, object-address, UUID, timestamp, random order, and Python hash iteration are not identity inputs.

## Exact ties

**Implementation choice: the paper does not specify exact objective ties.**

Selection key:

```text
(complete_objective_ascending, stable_full_strategy_identity_ascending)
```

The identity is a deterministic fallback only. It encodes no van-before-drone, drone-before-van, warehouse, route, distance, or random preference. The focused test reverses two equal-objective candidates and repeats selection three times; every run chooses the same complete identity and resulting State fingerprint.
