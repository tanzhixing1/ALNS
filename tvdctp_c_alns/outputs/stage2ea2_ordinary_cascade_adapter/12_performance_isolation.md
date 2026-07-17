# Performance isolation

All timings are seconds, three fixed-fixture/seed runs, median reported. The A.1
column was measured from a temporary `git archive` of commit `901ee48`; the A.2
column was measured from the current worktree in the same Python runtime.
Wall-clock values are diagnostic only.

| Existing pair | A.1 pair median | A.2 pair median | Adapter calls | Strict work-count result |
| --- | ---: | ---: | ---: | --- |
| Random+Global | 0.033190 | 0.026106 | 0 | unchanged |
| Random+Local | 0.021725 | 0.018226 | 0 | unchanged |
| Random+Regret | 0.130066 | 0.200821 | 0 | unchanged |
| Greedy+Global | 0.037220 | 0.035993 | 0 | unchanged |
| Greedy+Local | 0.028323 | 0.030407 | 0 | unchanged |
| Greedy+Regret | 0.144326 | 0.157916 | 0 | unchanged |
| Related+Global | 0.026169 | 0.026068 | 0 | unchanged |
| Related+Local | 0.019557 | 0.018719 | 0 | unchanged |
| Related+Regret | 0.125791 | 0.135817 | 0 | unchanged |
| Cascade+Global | 0.026992 | 0.029108 | 0 | unchanged |
| Cascade+Local | 0.018645 | 0.021576 | 0 | unchanged |
| Cascade+Regret | 0.134951 | 0.139097 | 0 | unchanged |
| Cascade+Cascade | 0.036061 | 0.038032 | 0 | unchanged (`6/5/4`, objective 4, checker 11) |

New-pair medians:

| Pair | Validation | Adapter total | Bundle construction | Ω(B) | Repair | Pair |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Random+Cascade | 0.002655 | 0.002787 | 0.000131 | 0.031026 | 0.037972 | 0.042994 |
| Greedy+Cascade | 0.002235 | 0.002382 | 0.000146 | 0.037252 | 0.043457 | 0.057541 |
| Related+Cascade | 0.002225 | 0.002340 | 0.000115 | 0.029833 | 0.036030 | 0.041758 |

Tests compare A.2 public repair boundaries with their unchanged direct bodies:
candidate traces, objective/checker calls and result fingerprints are identical.
No top-K, truncation, cache refactor, parallelism or performance optimization
was implemented.
