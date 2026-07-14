# Cascade metadata lifecycle

## Rules implemented

- At every registered destroy entry, the copied State drops only the three Cascade metadata keys before any destroy logic.
- Cascade removal replaces them with schema version 1, source operator, deterministic destroy call ID, source/destroyed fingerprints, ordered bundle IDs, and bundle fingerprints.
- A second Cascade destroy cannot inherit the first contract; its source business State and call ID are recomputed.
- A later non-Cascade destroy cannot expose old Cascade bundles to a repair.
- `TVDState.copy()` deep-copies the bundle list and top-level contract dictionary. Bundle contents are immutable tuples/frozen dataclasses.

## Pairing behavior

If Cascade removal is paired with a non-Cascade repair, metadata can remain on that candidate during the repair. Any business mutation makes `cascade_metadata_is_current` false, and the next destroy clears the keys. Changing the ALNS operator-pairing loop is unnecessary and was not done.

The current `cascade_repair` still has the known unsafe missing-metadata fallback to all `unassigned`; fixing or consuming the new contract belongs to Stage 2D.1 and was not performed here.

## Determinism and isolation evidence

- Three identical source/seed runs produce identical removed sets, ordered customer sets, IDs, canonical JSON, fingerprints, and top-level contract.
- Consecutive destroys produce different call/bundle IDs and the second source fingerprint matches the second pre-destroy business State.
- Replacing a snapshot and contract tuple in a copied State does not affect the original.
- Mutating the destroyed business State invalidates the contract validator.
