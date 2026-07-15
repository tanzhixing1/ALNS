# Static destroy → Cascade repair contract audit

## Consumer call chain

1. Public entry: `cascade_repair(state, rng, data, config)` at
   `operators.py:3541-3543`.
2. It copies the destroyed State and calls `_validated_cascade_bundles()` at
   `operators.py:3558-3560`.
3. `_validated_cascade_bundles()` reads `state.metadata["cascade_contract"]`,
   `cascade_bundles`, and later `cascade_removed` at
   `operators.py:3067-3097`.
4. `cascade_metadata_is_current()` requires schema version 1, source operator
   `cascade_aware_removal`, the exact destroyed-State fingerprint,
   `CascadeBundleSnapshot` instances, bundle IDs/fingerprints, destroy call ID,
   and source-State fingerprint (`operators.py:139-168`).
5. `_validate_bundle_snapshot()` checks bundle schema/source/revision,
   membership/order, service snapshots, route/sortie/launch/recovery/carrier
   snapshots, affected scope, and truck/warehouse context
   (`operators.py:2941-3064`).
6. Only after validation does the repair call
   `_enumerate_bundle_reconstruction_strategies()`
   (`operators.py:3593-3600`).

## Producer-consumer matrix

| Required Cascade field | Random writes | Greedy writes | Related writes | Cascade writes |
| --- | --- | --- | --- | --- |
| schema version | No | No | No | Yes |
| source operator | No | No | No | Yes: `cascade_aware_removal` |
| bundle IDs | No | No | No | Yes |
| customer membership snapshots | No | No | No | Yes |
| dependency order | No | No | No | Yes |
| affected route segments | No | No | No | Yes |
| removed drone sub-routes | No | No | No | Yes |
| launch/recovery snapshots | No | No | No | Yes |
| carrier snapshots | No | No | No | Yes |
| affected_structure_scope | No | No | No | Yes |
| source revision / fingerprints | No | No | No | Yes |

Random, Greedy, and Related each copy the input and immediately call
`_clear_stale_cascade_metadata()` (`operators.py:230-279`). Therefore they do
not merely omit new metadata: they deliberately prevent metadata from a prior
Cascade destroy from leaking into the next pair. The existing regression at
`tests/test_stage2d0_cascade_contract.py:379-409` verifies this for every
non-Cascade destroy.

Cascade removal also clears stale data first, then captures real snapshots
before removal and writes `cascade_removed`, `cascade_bundles`, and the contract
with schema, source, revision, source/destroyed fingerprints, bundle IDs, and
bundle fingerprints (`operators.py:581-658`). The immutable required bundle
fields are defined at `state.py:100-125`.

## Three compatibility layers

| Pair | Public-call compatible | Metadata-contract compatible | Semantically compatible |
| --- | --- | --- | --- |
| Random → Cascade repair | Yes | No | No |
| Greedy → Cascade repair | Yes | No | No |
| Related → Cascade repair | Yes | No | No |
| Cascade → Cascade repair | Yes | Yes | Yes |

## Failure paths

- Missing metadata: `_validated_cascade_bundles()` returns
  `None, ["missing cascade contract or bundle metadata"]`; public
  `cascade_repair()` returns a copied failure State with this diagnostic. It
  never enters legal `Omega(B)` construction.
- Stale fingerprint, wrong contract source, wrong schema, or top-level bundle
  mismatch: `cascade_metadata_is_current()` returns false and the validator
  reports `cascade contract is stale or does not match destroyed State`.
- A bundle-level source mismatch is separately checked at
  `operators.py:2949-2956`.

These are operator-contract failures, not empty feasible strategy sets and not
fixture infeasibility. Making the three pairs valid would require new producer
metadata or a changed Cascade consumer contract, both explicitly outside Stage
2E.
