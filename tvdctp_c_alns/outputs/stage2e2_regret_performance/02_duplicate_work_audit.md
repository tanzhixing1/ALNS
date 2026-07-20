# Duplicate Work Audit

Fixture: the deterministic second Regret call in the 20-customer/2-container/seed-42/paper-mode 10-iteration prefix (iteration 10, action 2).

Three clean replays produced identical business fingerprints and wall times `98.54826730000786`, `108.1723410000559`, and `110.11211839993484` seconds; median `108.1723410000559` seconds.

## Logical records versus business States

- All generated raw records from the persisted trace: `32,718`.
- Hard-feasible records entering exact scoring: `17,743`.
- Unique complete candidate identities within each customer/round dedup boundary: `17,743`.
- Duplicate candidate records removed by the existing identity dedup: `0`.
- Exact-scored candidate records: `17,743`.
- Unique pre-objective candidate business fingerprints: `17,743`.
- Duplicate pre-objective final business States: `0`.

Across different rounds, `9,545` scored move-identity occurrences repeat, but they are evaluated against different partial business States. They are not declared equivalent and must not be reused across State revisions.

## Repeated exact work

- Objective evaluations observed inside exact scoring: `17,770` (candidate records plus repeated base-State evaluations).
- Duplicate objective business-key evaluations: `26`, including `21` duplicate base evaluations.
- Canonical checker evaluations: `17,780`.
- Duplicate checker business-key evaluations after timing normalization: `1,215`.
- Candidate State copies: `17,787`.
- Candidate evaluation States discarded after scoring: `17,743`; the selected descriptor is reapplied to the working State, preserving the existing algorithm.

The three categories are intentionally distinct: there are no duplicate hard-feasible candidate records in this fixture, no duplicate pre-objective candidate business States, but there is repeated exact checker/timing work after deterministic State normalization.
