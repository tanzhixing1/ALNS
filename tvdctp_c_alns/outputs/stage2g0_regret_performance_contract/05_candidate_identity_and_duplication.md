# Candidate Identity and Duplication

## Definitions

- **Move identity** is the complete frozen tuple in
  `operators._regret_move_identity`: customer/mode, target route and insertion
  position or physical drone, launch/recovery vans/nodes/positions, sortie
  customers, container and assigned warehouse.
- **Business State identity** is `TVDState.cache_signature()`, excluding active
  removal context and audit-only diagnostics.
- **Evaluation identity** is the normalized business signature actually used by
  objective/checker after timing may resolve launch/recovery positions and assign
  derived physical-drone facts; data/config are frozen fixture inputs.

The heavy call has 32,718 local-prefilter attempts and 17,743
hard-feasible records. Per customer/revision dedup removed **0**. Across revisions,
only 8,198 complete move identities are globally
distinct (53.80% repeated occurrences), but those repeats
are evaluated on different partial States and are not reusable.

All 17,743 exact-scored candidate business States
are unique: business-State duplicate rate **0.00%**.
After deterministic timing normalization there are
16,557/17,743
unique evaluation identities, a 6.68% repetition rate.
This matches repeated within-candidate derived work, not duplicate logical moves.

Different moves can theoretically converge to one business State, but none did
in this fixture. Equal full business State plus identical data/config must produce
equal exact objective/checker results; Context-only differences are excluded.
Equal route geometry alone is insufficient because sortie positions, carriers,
unassigned/service state and normalized timing may differ.

**RESULT CACHE IS NOT PRIMARY OPTIMIZATION PATH.** The safe opportunity is a
single-candidate immutable evaluation context, not cross-round result reuse.
