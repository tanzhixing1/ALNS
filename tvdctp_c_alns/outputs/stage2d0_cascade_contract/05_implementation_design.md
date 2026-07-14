# Stage 2D.0 implementation design

## Data flow

1. Every destroy entry copies its input and clears only `cascade_removed`, `cascade_bundles`, and `cascade_contract`.
2. Cascade removal computes a deterministic source business fingerprint before selection/removal.
3. Existing random selection, dependency closure, and bundle partition execute unchanged.
4. Each already-formed bundle is captured from the intact copied State.
5. Existing diagnostics and `_remove_customers` execute unchanged.
6. A destroyed-business fingerprint is computed and the structured bundle list plus top-level contract is attached.

The deterministic destroy call ID hashes schema, operator, source fingerprint, initial selection, final removal, and ordered bundle membership. Bundle IDs add the existing bundle index. No time, UUID, new random call, or random-state consumption is used.

## Lifecycle

`cascade_metadata_is_current(state)` validates schema, source operator, destroyed-State fingerprint, bundle types, IDs, bundle fingerprints, destroy call ID, and source fingerprint. Stage 2D.0 exposes the validator but deliberately does not modify `cascade_repair` to consume it.

## Compatibility boundary

`CascadeBundleSnapshot` supports iteration over `customer_ids` only so the unchanged pre-Stage-2D.1 `cascade_repair` can continue reading its old customer-list view. This is a transport compatibility shim, not a `BundleReconstructionStrategy` and not a repair implementation.

## Explicit exclusions

- No Cascade repair changes.
- No candidate generation or candidate scoring.
- No dependency propagation, partition, ordering, selection, or removal changes.
- No checker, objective, registry, SA, or ALNS-loop changes.
- No whole-State snapshot, guessed relationship, top-K, beam, or pruning.
