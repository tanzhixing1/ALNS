# Native / Ordinary Adapter Boundary

| Boundary | Result |
|---|---|
| Native Cascade destroy ordinary-adapter calls | 0 across IDs 12–15 |
| Random + Cascade | exactly 1 ordinary-adapter call |
| Greedy + Cascade | exactly 1 ordinary-adapter call |
| Related + Cascade | exactly 1 ordinary-adapter call |
| Ordinary adapter enlarges actual R | no |
| Ordinary path calls Native graph | no |
| Native partition replaced by ordinary partition | no |
| Shared mutable temporary state | none observed; all returned/source/destroyed contexts clean |

The adapter consumes only an ordinary `RemovalStructuralContext`; Native supplies its own `CascadeBundleSnapshot`/contract and bypasses adaptation. The full Stage 2E-A.2 file passed 33/33, including lazy invocation, Native bypass, real Ω(B), no fallback, empty Ω(B), rollback, and deterministic three-run cases.

```text
NATIVE/ADAPTER BOUNDARY PASS
```
