# Structural fingerprint isolation

The new dedicated function is
`structural_business_fingerprint(StructuralProjection)`, implemented as SHA-256
of canonical UTF-8 JSON.

`context_id` is SHA-256 of version/source, pre/post fingerprints, selected and
actual IDs, and the three ordered removal observations. It does not call any
RNG and excludes itself.

Isolation evidence:

- adding/removing the active context leaves the dedicated projection digest
  unchanged;
- `TVDState.cache_signature()` is unchanged;
- existing `operators._state_business_fingerprint()` / Stage 2D stale contract
  fingerprint is unchanged;
- objective/checker/candidate business identity do not read the active key;
- three independent runs per destroy produce identical context, ID, footprint,
  business result and RNG state;
- different removed/post structures produce different IDs.

The existing canonical State fingerprint and Stage 2D source fingerprint were
not redefined.
