# Stage 2F.2 Regression Plan

This is a test design only. No test was added or modified in Stage 2F.0. All tests use small deterministic States; no 20-customer, 80-iteration, or performance gate belongs here.

## A. Paper-semantic tests

1. **Seed provenance**: fixed RNG returns known `R^(0)`; assert `customer_selection_order` equals only seeds, while selected/final IDs include closure additions.
2. **Same-sub-route dependency**: seeding a sortie customer or customer-valued anchor yields the full accepted same-sub-route customer dependency set.
3. **Explicit coordination dependency**: one fixture for every MED-2 edge kind, including receiving-van/carrier-transfer linkage when represented.
4. **Unrelated exclusion**: a customer on an unrelated route/sortie/warehouse is never added merely because it shares a vehicle class or transshipment.
5. **Recursive chain**: `a -> b -> c` requires more than one expansion wave and yields exactly `{a,b,c}`.
6. **Cycle**: `a -> b -> c -> a` terminates with unique membership and no cap/fallback.
7. **Multiple sources and duplicate target**: two sources discover the same third customer; the customer occurs once in `R*`, while provenance records the defined evidence policy.
8. **Final `R*` transition**: actual pre/post unassigned difference and `cascade_removed` equal the computed closure.
9. **Simultaneous structural removal**: associated drone sub-routes/route segments/coordination snapshots are captured before mutation and removed/represented together.
10. **Partition**: weak dependency components form disjoint bundles whose union equals `R*`; isolated nodes are singleton bundles.
11. **Order policy**: bundle order and ascending-ID `dependency_order` follow the declared MED rules, explicitly labeled paper-unspecified.
12. **No infeasible truncation**: closure is not cut because repair may later fail; malformed structure fails fast rather than silently falling back.

## B. Determinism tests

For each semantic fixture, run Native Cascade at least twice with a fresh State and fresh generator initialized to the same seed. Assert equality of:

- initial business/structural fingerprints;
- observable RNG calls and arguments;
- seed customer(s) and initial set;
- dependency edge evidence and discovery sequence;
- `R*`;
- deletion/actual-unassignment order;
- bundle membership and bundle order;
- `dependency_order`;
- bundle canonical JSON/fingerprints and destroy-call ID;
- destroyed business fingerprint and context ID.

Add one subprocess test or documented multi-process probe so determinism does not accidentally depend on Python set iteration.

## C. Native/adapter boundary

1. Monkeypatch adapter entry to fail; Native Cascade + Cascade must never call it.
2. Random + Cascade calls the adapter exactly once.
3. Greedy + Cascade calls it exactly once.
4. Related + Cascade calls it exactly once.
5. Adapter bundle union equals ordinary `actually_unassigned`; it never expands that set.
6. Ordinary destroy RNG traces and business fingerprints remain frozen before versus after Stage 2F.1.
7. Native corrected dependency logic is not imported/called by ordinary adapter paths unless explicitly read-only and proven semantically neutral.

## D. Context lifecycle

1. Destroyed disposable candidate carries exactly one valid immutable context.
2. Global/Local/Regret repair boundary consumes/discards context and never returns it.
3. Cascade repair detaches context, uses Native metadata or ordinary adapter appropriately, and cleans success/failure paths.
4. Current and best have no active context before and after every solver iteration.
5. Cascade repair failure, adapter rejection, canonical-checker rejection, and raised exception leave no context on any persistent or returned State.
6. Copy isolation remains exact: context is immutable while other metadata is deep-copied.

## E. Stable 16-pair contract

1. Omitted mode resolves to `paper_mode`.
2. Destroy order and repair order remain the frozen 4×4 Cartesian product.
3. IDs 0–15 and registry fingerprint remain exact; Native Cascade + Cascade stays 15.
4. Every pair resolves and executes on the small deterministic fixture.
5. No fallback, reroll, action masking, or hidden pair substitution occurs.
6. Missing production registry binding remains fail-fast.
7. `extended_mode` remains explicit-only and its existing IDs/rules remain unchanged.

## F. Repair and system invariance

Use monkeypatch canaries and diff review to prove Stage 2F changes removal only:

- Cascade `Ω(B)` enumeration, validation, objective scoring, stable strategy identity, and atomic failure unchanged;
- Global, Local, true Regret-2 source and call counts unchanged;
- candidate generation, objective, checker, timing, State, and `State.copy` source hashes unchanged;
- SA acceptance, temperature, adaptive scores/weights, and action selection unchanged;
- focused pre-Stage2F repair baselines remain exact when given an unchanged bundle contract.

## G. Small-run gate

1. Run the corrected Native removal fixtures and the existing cascade-contract/context/adapter/operator-mode focused suites.
2. Run the full test suite only if practical; if a known unrelated medium test times out, report a baseline-relative grouped result without claiming a full-suite pass.
3. No performance speedup or memory target is imposed.

## Required evidence outputs for Stage 2F.2

- before/after fixture comparison CSV;
- RNG trace CSV;
- paper-semantic focused test result;
- Native/adapter/lifecycle result;
- 16-pair registry and execution result;
- repair-isolation/source-hash report;
- final scoped diff and Git gate.

