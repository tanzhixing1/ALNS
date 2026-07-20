# Optimization Design and Disposition

## Evaluated prototype

A single-`regret_repair` exact cache was prototyped with deterministic
`sha256(repr(state.cache_signature()))` keys and separate `objective`,
`canonical_checker`, and `timing` namespaces. Candidate records, identities,
enumeration order, ranking, and selected moves remained present; cache storage was
discarded in `finally` after each repair call.

The timing namespace stored exact timing under the signatures immediately before
and after timing normalization. This targeted the measured objective-to-checker
recomputation without approximate scoring or candidate pruning.

## Decision

The prototype is **rejected and reverted**:

- focused median: `108.1723410000559 s` to `100.84321289998479 s`;
- wall reduction: `6.775417849251609%`, below the required `30%`;
- combined actual objective/checker evaluations: `35,550` to `34,317`;
- call reduction: `3.468354430379747%`, below the required `40%`;
- the implementation touched objective/checker source and changed Stage 2E.1
  work counters, violating the requested source-isolation/regression canaries.

No second high-risk optimization was attempted because incremental Regret updates,
cross-customer reuse, pruning, approximation, and parallel scoring are explicitly
out of scope. Final production code is identical to baseline HEAD.
