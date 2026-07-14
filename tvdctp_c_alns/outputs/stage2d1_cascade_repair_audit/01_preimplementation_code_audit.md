# Stage 2D.1 preimplementation code audit

This audit was completed after `GIT PROVENANCE PASS` and before modifying production code.

## 1. Current `cascade_repair` call chain

```text
cascade_repair
  -> copy input State
  -> read metadata["cascade_bundles"]
     or fallback to [all State.unassigned]
  -> reorder every bundle high-floor-first then customer ID
  -> for each bundle: _best_bundle_repair
     -> _repair_bundle_all_van
     -> _repair_bundle_best_modes
     -> _repair_bundle_as_drone
     -> _repair_bundle_partial_candidates (only bundle sizes 2-3)
     -> for every candidate: _finish_repair
     -> _candidate_score
  -> when no candidate: per-customer _all_moves fallback
  -> final sorted sweep over every remaining State.unassigned
  -> _finalize_repair
     -> consolidate_drone_sorties over the whole State
```

Global, Local, Regret, and the public Best-mode repair functions are not directly called, but generic per-customer `_all_moves` and the same low-level insertion helpers are reused.

## 2. Current `_best_bundle_repair()` behavior

It builds a small fixed candidate family: sequential all-van, sequential best-mode, one all-bundle drone sortie, and—for bundle sizes 2-3—proper subsets served by one drone sortie with the rest inserted sequentially by van. Each preliminary bundle candidate is then passed to `_finish_repair`, scored only after global completion, and selected by `(objective only, generation order on exact ties)`. It does not retain a stable complete bundle-strategy identity and does not jointly validate the bundle while later bundles remain unassigned.

## 3. `_finish_repair()` global scope

`_finish_repair()` copies its input and repeatedly loops over `finished.unassigned.copy()`. For every customer it calls `_all_moves` and applies the first move. There is no bundle membership or affected-structure argument, so a candidate for the first bundle can repair later bundles and unrelated external unassigned customers.

## 4. Why `_candidate_score()` requires complete service

`_candidate_score()` calls the canonical `check_solution_feasible` and returns `None` for any violation. The checker emits `unassigned customers remain: [...]` whenever any customer remains unassigned. Therefore a correctly bundle-scoped intermediate candidate cannot pass while later bundles or external customers remain unassigned; the existing implementation works around that by globally completing the State before scoring.

## 5. Current global sortie consolidation scope

`_finalize_repair()` unconditionally calls `consolidate_drone_sorties`. That helper groups every sortie in the State by anchors/vans and repeatedly merges compatible groups. It can therefore actively rewrite bundle-external sorties. Cascade repair has no scope argument for consolidation.

## 6. Metadata-missing fallback

`raw_bundles = repaired.metadata.get("cascade_bundles") or [repaired.unassigned.copy()]` silently treats all unassigned customers as one Cascade bundle. There is no schema, source operator, contract fingerprint, destroyed-State fingerprint, bundle ID, membership, structural snapshot, or affected-scope validation at repair entry.

## 7. Current failure return semantics

If `_best_bundle_repair()` returns `None`, Cascade repair falls back to independent `_all_moves` for that bundle. It then performs another global all-unassigned sweep. If customers remain impossible, it returns the partially modified State; the outer ALNS full-feasibility flow may reject it. Earlier bundle changes are not rolled back when a later bundle fails.

## 8. Reusable reconstruction helpers

- `_enumerate_feasible_van_moves` enumerates all concrete hard-feasible van insertions for one customer.
- `_enumerate_feasible_drone_moves_for_customers` enumerates all concrete anchors, same/cross-van recovery choices, and physical drone choices for one supplied customer sequence.
- `_apply_move` applies one van insertion or one complete drone sortie and updates service/unassigned fields.
- `_best_drone_move_for_customers` supports a complete supplied customer list and cross-van recovery, but returns only its locally cheapest move.
- State snapshots preserve original van segment, sortie, launch/recovery, carrier-transfer, and truck/container context.

There is no existing helper that directly restores a full `CascadeBundleSnapshot` or atomically represents its complete reconstructed State.

## 9. Generic/global helpers

- `_all_moves`, `_finish_repair`, and the final unassigned sweep are generic repair-all-unassigned mechanisms.
- `_extend_drone_customers` scans all `state.unassigned` and is unsafe for bundle-scoped candidate generation.
- `consolidate_drone_sorties` is global.
- `_candidate_score` requires full feasibility and cannot directly validate an intermediate bundle.
- `_repair_bundle_best_modes` and `_repair_bundle_all_van` are sequential per-customer greedy builders.

## 10. Functions to replace or scope-limit

- Replace the Cascade path through `_best_bundle_repair` with `BundleReconstructionStrategy` enumeration, stable identity, exact full-objective ranking, and atomic application.
- Cascade repair must not call `_finish_repair`, public/global repair operators, the generic repair-all-unassigned sweep, or the global `_finalize_repair` path.
- Add a thin partial-validation wrapper around the canonical checker that ignores only the exact missing-service violation caused exclusively by an explicit `allowed_unassigned` set.
- Limit any Cascade consolidation/reconstruction to IDs in the current bundle's `affected_structure_scope`; unchanged external structural projections must be checked before candidate acceptance.
- Missing or invalid metadata must return an untouched destroyed-State copy with explicit diagnostics.
- Preserve the existing full checker and objective semantics.

## Preimplementation conclusion

The Stage 2D.0 contract is sufficient to stop guessing destroyed relationships. The current Cascade repair implementation violates bundle-only scope, separate bundle processing, atomic failure, strict metadata handling, stable exact-tie behavior, and scoped consolidation. Those paths must be replaced only inside Cascade-specific code; Cascade removal selection/closure/partition, Global, Local, Regret, registry, objective, checker semantics, and ALNS main loop remain out of scope.
