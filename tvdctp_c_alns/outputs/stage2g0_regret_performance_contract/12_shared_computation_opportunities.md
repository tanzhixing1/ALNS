# Shared Computation Opportunities

```text
candidate move
  -> full materialized State
  -> business signature
  -> derived timing + physical carrier facts
  -> objective cost terms
  -> canonical checker rules
  -> normalized evaluation identity
```

Current clean counts are 17,784 objective,
17,792 checker, 35,496 timing and
71,072 signature calls. Timing is requested almost twice
per objective candidate, with only 48 hits. Objective
computes waiting/timing, then checker requests timing again; in-place normalization
can change the lookup signature.

Safe Stage 2G.1 opportunity: construct one immutable, candidate-scoped derived
context after materialization and let exact objective/checker consume the same
timing/physical-route/structural facts. It must be keyed by the complete frozen
business input plus data/config identity, never persist across State revision,
and invalidate on any route/sortie/service/unassigned/carrier/container-readiness
change. Final outputs remain production objective/checker values.

Cross-candidate result cache is not primary: business duplicate rate is
0.00%. Candidate representation/copy-on-write is a
separate Class 2 opportunity for Stage 2G.2.
