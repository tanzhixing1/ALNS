# Preimplementation destroy-to-repair contract audit

This records the behavior before Stage 2D.0 changes.

| Question | Finding |
|---|---|
| How bundles are formed | Initial randomly selected served customers are closed through `_cascade_dependencies`, which currently follows touched drone sorties. Each pre-removal sortie contributes `sorted(related ∩ removal)`; remaining removed customers become sorted singletons. |
| When metadata is written | `cascade_removed` and `cascade_bundles` were written only after `_remove_customers` and unassigned deduplication. |
| When structures are deleted | `_remove_customer` first removes matching van-route nodes, then removes every sortie whose customer/launch/recovery touches that customer, then marks the touched sortie customers and target customer unassigned. |
| Irrecoverable after destroy | Original service mode, van ID and route position, removed route neighborhood, complete touched sortie, explicit launch/recovery vans and positions, physical drone/carrier transfer, and the exact pre-destroy structural association. |
| `State.copy` behavior | `metadata`, `drone_sorties`, `van_routes`, assignments, container routes, tractor routes, and timing are deep-copied. |
| `_apply_move` / repair / checker effects | `_apply_move` changes routes, sorties, service mode, and unassigned but does not consume Cascade metadata. Objective/checker may refresh timing/cache diagnostics; they do not validate Cascade origin or freshness. |
| Later non-Cascade destroy | Before Stage 2D.0 it copied and retained old Cascade metadata, permitting stale reuse. |
| Cascade destroy + non-Cascade repair | Metadata survived repair and could survive into later iterations; no lifecycle boundary existed. |
| Customer order stability | Each existing bundle is `sorted(...)`; singleton remainder is also sorted. This is deterministic current implementation order, not a paper dependency order. |
| Bundle order stability | Drone-sortie list order first, then sorted singleton remainder. Deterministic for an identical State, but Paper unspecified. |

The pre-audit also confirmed that `_best_bundle_repair` calls `_finish_repair`, which traverses the whole State `unassigned`; the first bundle can therefore repair later bundles and external customers. Stage 2D.0 does not change that repair code.
