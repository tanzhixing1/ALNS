# Cascade Repair Consumption Contract

## Frozen implementation check

Between `760e3bc...` and `9488139b...`, the only changed production blob is `operators.py`, and its diff ends inside Native removal. There is no diff in `_restore_snapshot_strategy_state`, `_van_block_strategy_states`, `_drone_bundle_strategy_states`, `_validate_cascade_candidate`, `_enumerate_bundle_reconstruction_strategies`, scoring, selection or `cascade_repair`.

The blobs for `removal_structural_context.py`, `state.py`, `feasibility.py`, `objective.py` and `alns_solver.py` are identical between the two commits. Therefore Cascade Ψ(B), checker, objective, State, solver acceptance and RNG machinery are frozen.

## Extra raw candidate checklist

| Question | Result | Evidence |
|---|---|---|
| generated naturally by existing Ψ(B) from legal bundle | YES | `_restore_snapshot_strategy_state` returns the sole raw State |
| Stage 2F.1 special candidate | NO | repair-side source has no diff |
| fallback | NO | source kind is `snapshot`; fallback spies remain green |
| reroll | NO | repair RNG unchanged |
| duplicate | NO | unique State fingerprint; only one raw candidate |
| ordinary adapter product | NO | Native source contract; adapter bypass test passes |
| canonical validation reached | YES | exactly one `_validate_cascade_candidate` call |
| checker result correct | YES | reports explicit hard-floor wrong-mode violations |
| blocks objective scoring | YES | feasible/unique strategies 0; objective calls 0 |
| failure/rollback follows Stage 2D | YES | returns original destroyed business fingerprint and clears context |

The formal boundary is necessary. Removing it would allow a candidate that is not canonically hard-feasible to enter objective scoring, directly contradicting the Stage 2D partial-validation contract.

```text
CASCADE REPAIR CONSUMPTION CONTRACT PASS
```

