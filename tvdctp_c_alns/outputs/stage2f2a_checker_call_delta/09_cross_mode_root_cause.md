# Cross-mode Root Cause

The two +1 deltas have the same root cause.

| Property | Paper | Extended |
|---|---|---|
| Extra call index | 484 | 322 |
| Iteration | 7 | 8 |
| Action | 15 | 15 |
| Caller | `_validate_cascade_candidate` | same |
| Stack | Native action → Cascade enumeration → validation | same |
| State class | disposable snapshot candidate | same |
| Checker result | infeasible | infeasible |
| Native actually selected | yes | yes |

The source is not a mode-specific solver path, test teardown, final-best validation, test accounting wrapper, or newly added checker call site. It is the shared Native Cascade + Cascade action.

Why exactly +1 in both modes:

1. Each frozen 12-iteration action sequence selects action 15 exactly once.
2. Baseline Native output causes Cascade contract validation to abort before candidate validation, so this action contributes zero `_validate_cascade_candidate` calls.
3. Current Stage 2F.1 Native output supplies one valid bundle and exactly one raw snapshot candidate.
4. The pre-existing canonical boundary validates that candidate exactly once and rejects it.
5. No strategy reaches objective scoring; all later calls realign.

Thus the shared root is Stage 2F.1's corrected Native bundle reachability changing Cascade repair control flow, not a checker/solver/test implementation change.

