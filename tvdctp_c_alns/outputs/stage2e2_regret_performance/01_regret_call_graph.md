# Regret-2 Call Graph Audit

The production path is:

```text
regret_repair
  -> copy destroyed State once
  -> for every remaining unassigned customer, in original order
     -> enumerate every hard-feasible van move
     -> enumerate every hard-feasible drone move
     -> deduplicate only complete move identities
     -> for every retained move
        -> State.copy
        -> apply the concrete move
        -> exact objective
           -> compute_waiting_minutes / compute_timing
           -> canonical checker
              -> compute_timing again
     -> stable exact-cost sort (van before drone, then complete identity)
     -> retain exact first and second candidate
     -> Regret(i) = f2 - f1
  -> choose maximum regret by existing priority key
  -> apply the selected concrete move to the working State
  -> recompute every remaining customer in the next round
```

No RNG call occurs inside the Regret-2 enumeration/ranking path. The repair receives the production RNG but does not advance it.

The existing general caches are keyed by `(id(state), state.cache_signature())`. Consequently, two separately copied States with the same business signature cannot share exact results. In addition, `compute_timing` can normalize launch/recovery position hints. Its first cache entry is written under the pre-normalization signature, so the checker can immediately miss that entry under the post-normalization signature and recompute timing for the same candidate.

Safe optimization point: an invocation-local exact cache plus publication of the already-computed timing under the post-normalization signature, active only during one `regret_repair` call. This retains every logical record and every exact result while eliminating repeated evaluation work.
