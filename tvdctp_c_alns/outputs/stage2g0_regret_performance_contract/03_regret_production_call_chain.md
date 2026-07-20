# True Regret-2 Production Call Chain

```text
regret_repair
  -> copy destroyed State once
  -> while unassigned remains
     -> evaluate every remaining customer (27 customer-evaluations over 6 rounds)
        -> enumerate every van insertion -> hard local prefilter
        -> enumerate every drone tuple/launch/drone/recovery -> hard local prefilter
        -> deduplicate complete move identity
        -> base objective on a State copy
        -> for every retained move
           -> State.copy -> apply concrete move
           -> objective -> waiting -> compute_timing
           -> canonical checker -> compute_timing lookup/recompute
        -> stable exact-cost sort, van-before-drone, complete identity
        -> first/second and Regret=f2-f1
     -> select maximum-regret customer
     -> apply selected move in-place
  -> repeat all remaining customer evaluations
  -> production finalize/consolidation/check
```

The clean call selected customers `[16, 23, 22, 24, 7, 13]` and performed six
in-place commits. No RNG is consumed inside Regret enumeration/ranking.

Inclusive and exclusive timings and allocation evidence are in `03a`. Times are
nested: objective includes timing and checker, and checker includes timing.
