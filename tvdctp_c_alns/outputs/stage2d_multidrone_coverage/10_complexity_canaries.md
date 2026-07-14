# Complexity canaries

Fixed fixture, seed 29, three identical runs:

| Canary | Value |
| --- | ---: |
| Bundle count | 2 |
| Bundle sizes | 2, 2 |
| Raw candidates | 9, 100 |
| Feasible candidates | 9, 100 |
| Unique candidates | 9, 100 |
| State copies | 111 |
| Objective calls | 109 |
| Checker calls | 219 |
| Maximum Cascade depth | 1 |
| Lossy truncation | false |
| Customer Cartesian product | false |

The expected cost of this correctness fix is a multiplicative named-drone
dimension in the existing whole-sortie loops. In the fixed fixture, two eligible
named drones exactly double only the drone-bundle family. No new candidate
family, recursion, per-customer Cartesian product, top-K, beam, or cutoff was
introduced. Symmetry reduction, if ever desired, requires a separate proof and
belongs to later performance work, not this Stage 2D closure.
