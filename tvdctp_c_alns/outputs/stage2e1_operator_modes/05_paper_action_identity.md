# Frozen paper action identity

| ID | Destroy | Repair |
| ---: | --- | --- |
| 0 | Random | Global |
| 1 | Random | Local |
| 2 | Random | Regret |
| 3 | Random | Cascade |
| 4 | Greedy | Global |
| 5 | Greedy | Local |
| 6 | Greedy | Regret |
| 7 | Greedy | Cascade |
| 8 | Related | Global |
| 9 | Related | Local |
| 10 | Related | Regret |
| 11 | Related | Cascade |
| 12 | Cascade | Global |
| 13 | Cascade | Local |
| 14 | Cascade | Regret |
| 15 | Cascade | Cascade |

`ActionIdentity` and `ActionRegistry` are frozen dataclasses; actions and
bindings are tuples. IDs are exactly 0..15, pairs are unique, and the complete
4 x 4 cartesian product is asserted. Lookup failure is explicit and never
returns `None`, `-1`, a nearest match, or a substitute pair.
