# Atomic failure and metadata design

## Entry validation

Repair validates before constructing a strategy:

- contract and bundle metadata exist;
- schema version and source operator;
- destroyed-State business fingerprint;
- destroy call/revision and pre-destroy source fingerprint;
- unique bundle IDs and disjoint memberships;
- `cascade_removed` equals the bundle-membership union;
- every bundle customer is currently unassigned;
- exact service snapshot membership and valid original modes;
- dependency order is a permutation of membership with the declared semantics;
- route, sortie, launch/recovery, carrier, truck/warehouse snapshots;
- exact `affected_structure_scope` IDs derived from those snapshots.

Missing/stale/invalid metadata returns a destroyed-State copy with `cascade_repair_diagnostics.status="failure"`. It never infers a bundle from all unassigned customers.

## Empty `Ω(B)`

**Implementation choice: the paper does not explicitly specify this detail.**

If any bundle has no feasible complete strategy, the entire call returns `repair_base`, discarding all earlier working-State changes. There is no call to Global, Local, Regret, Best-mode, `_finish_repair`, `_all_moves`, repair-all-unassigned, or global sortie consolidation.

The input State is never mutated. All work occurs on counted deep copies. The returned failure copy contains the original destroyed business State plus diagnostics.

## Metadata lifecycle

On both success and failure, `cascade_removed`, `cascade_bundles`, and `cascade_contract` are consumed/cleared from the returned State so a later non-Cascade operation cannot reuse them. Diagnostics are deep-copy isolated by `TVDState.copy()`. Consecutive destroy/repair cycles receive a fresh contract and do not chain to the prior cycle.
