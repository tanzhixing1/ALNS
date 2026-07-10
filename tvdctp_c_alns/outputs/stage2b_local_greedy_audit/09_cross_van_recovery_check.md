# Cross-van recovery check

Focused test: `test_local_scope_preserves_cross_van_recovery`.

The state has two vans at the selected warehouse. Local drone generation is called with the launch scope containing only the target launch van. Distances make recovery at a node on the second van preferable and legal.

Observed:

- launch van equals the Local target van;
- recovery van differs from launch van;
- the scoped generator returns the cross-van move;
- `_apply_move` applies it through the shared path;
- `check_solution_feasible` returns `(True, [])`.

Implementation scope is intentionally asymmetric: launch is filtered by `allowed_launch_van_ids`, while the recovery loop remains over all existing routes. No top-k, nearest-node, fixed-recovery-van, or distance-threshold pruning was added.
