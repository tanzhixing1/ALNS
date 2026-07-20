# Current Native Cascade Behavior Snapshot

## Fixture and method

The audit reused `_coordinated_fixture` from `tests/test_stage2d0_cascade_contract.py`. That fixture is generated through production configuration/data/initial-solution code and is explicitly checked by the canonical checker before every probe run. Its initial business fingerprint is:

`b9f9ede9f8a413b4e214e3afa4d98e9111c0e79b6945e9e57e9bc64a0a5048dc`

Served customer order is `[5, 6, 7, 8, 9, 10, 11, 12]`. Relevant identities are: same-sortie anchor `5`, cross-van recovery anchor `6`, same-sortie drone customer `7`, cross-van drone customer `8`, and plain van customer `9`. The source State is canonical-feasible (`True, []`).

Each case used production `cascade_aware_removal` with a fresh `RecordingRng`, fresh fixture State, and the same seed for two independent runs. `current_behavior_raw.json` contains the full records.

## Case snapshots

### 1. `single_cross_van_chain` — seed 1, requested count 1

- RNG call: `choice([5,6,7,8,9,10,11,12], size=1, replace=False)`
- Seed customer / initial set: `8` / `[8]`
- Expansion: source `8` adds `6`
- Final current-implementation closure: `[6, 8]`
- Deletion/removal order: `[8, 6]`
- Actual unassignment order: `[8, 6]`
- Dependency map over final members: `6 -> {6,8}`, `8 -> {6,8}`
- Bundle partition: `[[6,8]]`
- `dependency_order`: `[[6,8]]`
- Destroyed business fingerprint: `e877c3666cacb4ff1af0f567ec23f89eba89a748c168b1c0c0e8504f8b00d12c`
- Context trace: `[(8,6)]`; Native partition/order evidence matches the bundle.
- Cascade repair input: one valid Native bundle, active Native context present, zero contract errors.

This is a single dependency chain involving a drone customer and its customer-valued receiving anchor on a different van.

### 2. `same_sortie_duplicate_membership` — seed 23, requested count 1

- RNG call: one `choice`, size 1, no replacement
- Seed customer / initial set: `5` / `[5]`
- Expansion: source `5` adds `7`
- Final current-implementation closure: `[5, 7]`
- Removal and actual-unassignment order: `[5,7]`
- Dependency map: both `5` and `7` return `{5,7}`
- Bundle partition / `dependency_order`: `[[5,7]]`
- Destroyed fingerprint: `dc758e7946c8938fb6031fc95af3c0537129893d767e23d6306a6307572e8b4d`
- Context trace records only the newly discovered edge `[(5,7)]`; the already present reverse/co-membership fact is suppressed by set membership.
- Cascade repair input: valid, one bundle, zero errors.

This demonstrates duplicate customer membership suppression inside a same-sortie dependency set. A reliable existing fixture in which two distinct sources discover the same previously unseen third customer in one expansion round was not available; that narrower provenance scenario is an **EVIDENCE GAP: RELIABLE FIXTURE NOT AVAILABLE** and belongs in Stage 2F.2.

### 3. `two_dependency_chains_two_bundles` — seed 58, requested count 2

- RNG result / initial set: `[8,7]`
- Expansion sequence: `8 -> 6`, then `7 -> 5`
- Final current-implementation closure: `[5,6,7,8]`
- Deletion order: `[5,6,7,8]`
- Actual unassignment order: `[5,7,6,8]` because removing an anchor removes its associated sortie customers.
- Bundle partition: `[[5,7],[6,8]]`
- `dependency_order`: `[[5,7],[6,8]]`
- Destroyed fingerprint: `f6b8b4e95962feba350fcfba08e04922575dfba3beea3389fbe42cc1420bd37e`
- Cascade repair input: two disjoint valid bundles, zero errors.

This covers multiple initial customers, multiple dependency additions, two chains, and multiple bundles.

### 4. `two_seed_two_chain_order` — seed 48, requested count 2

- RNG result / initial set: `[8,5]`
- Expansion: `8 -> 6`, then `5 -> 7`
- Final closure, deletion order, actual-unassignment order, partition, order, and destroyed fingerprint are identical to case 3.
- The context ID differs because seed provenance and expansion trace differ, while the destroyed business State is the same.

This confirms that distinct seed provenance can converge to the same current closure/business State while remaining distinguishable in context evidence.

## Determinism result

For all four cases, run 1 and run 2 agreed on:

- initial State fingerprint;
- observable RNG call and arguments;
- seed customer and initial selected set;
- dependency expansion sequence;
- final closure;
- removal order;
- bundle partition;
- `dependency_order`;
- destroyed State fingerprint.

Result: **CURRENT NATIVE CASCADE BEHAVIOR DETERMINISTIC on the audited baseline and reliable fixture**.

This is a baseline observation, not a proof across Python/NumPy versions. The code iterates a Python set during closure and removal, so explicit ordered traversal remains preferable for a future cross-runtime contract.

## Focused existing-test evidence

The following read-only focused test selection passed:

- all `tests/test_stage2d0_cascade_contract.py` tests;
- Native Cascade bypasses the ordinary adapter and remains exact;
- Native structural context matches the frozen pre-context contract;
- selected IDs and actual unassigned IDs remain distinct facts;
- Native Cascade + Cascade remains action ID 15.

Result: `22 passed in 3.37s` (pytest wall output `8.1s`). Tests and production were not modified.

## Important naming caveat

Fields named `final_removal_set_R_star` in raw evidence mean “the current implementation’s computed fixed point.” Because the production dependency predicate is only a subset of the paper’s partially described truck–van–drone dependency relation, this audit does **not** certify that the current set equals the paper-intended `R*`.

