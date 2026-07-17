# New three-pair evidence

Fixture: coordinated Stage 2D fixture, removal count 1, NumPy seed 29.

| Pair | Adapter calls | Raw/feasible/unique Ω(B) | Status | Objective | Feasible | Final fingerprint |
| --- | ---: | --- | --- | ---: | --- | --- |
| Random + Cascade | 1 | 6/5/4 | success | 927.880274815561 | YES | `56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e` |
| Greedy + Cascade | 1 | 11/11/10 | success | 791.639335388478 | YES | `b29d4743a67273b3908cd26e1f4a95c634829d3a50aae1cc7596cf5803ee5cb3` |
| Related + Cascade | 1 | 6/5/4 | success | 927.880274815561 | YES | `56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e` |

All three invoke `_enumerate_bundle_reconstruction_strategies`, use exact
objective scoring, return context-free candidates and call no other repair
fallback.
