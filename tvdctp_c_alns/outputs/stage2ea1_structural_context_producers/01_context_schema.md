# RemovalStructuralContext schema

Implementation: `removal_structural_context.py`.

`RemovalStructuralContext` is a frozen dataclass whose complete descendant
graph consists of frozen dataclasses, tuples and scalar primitives. It stores
no live `TVDState`, route list, sortie dict, RNG, UUID or object identity.

Required fields are implemented directly:

- version/identity: `schema_version`, `structural_context_version`,
  `context_id`, `source_destroy_operator`, `producer_capabilities`;
- fingerprints: `pre_destroy_structural_fingerprint`,
  `post_destroy_structural_fingerprint`;
- removal facts: `selected_removed_customer_ids`,
  `actually_unassigned_customer_ids`, `removal_order`, plus the disambiguated
  selection/deletion/actual-unassignment orders;
- immutable pre/post structural projections;
- customer service, route position/segment, drone sortie, launch/recovery,
  carrier-transfer and coordination-edge facts;
- authoritative `mutation_footprint` and factual
  `external_boundary_entities`/projection;
- optional Cascade producer evidence: dependency trace, native partition and
  native dependency order.

Forbidden repair concepts are absent: ordinary repair bundles, ordinary
dependency order, repair strategy/candidate/selection, objective value, top-K,
beam and candidate truncation.

The context is stable-JSON serializable with sorted keys, compact separators,
UTF-8 and `allow_nan=False`. Context validation recomputes both structural
fingerprints, actual-unassigned transition, mutation diff, external boundary,
trusted capabilities and context ID.
