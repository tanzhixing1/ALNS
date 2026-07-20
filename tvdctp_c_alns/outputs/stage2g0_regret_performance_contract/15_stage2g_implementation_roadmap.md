# Stage 2G Implementation Roadmap

1. **Stage 2G.1 — Shared Evaluation Context.** First target repeated exact
   timing/signature/structural traversal inside one materialized candidate.
   Objective and canonical checker must retain exact output APIs and consume one
   immutable context. Risk: low-to-medium; expected gain source is removal of the
   second timing traversal and repeated signature/physical-route derivation.
2. **Stage 2G.2 — Candidate Representation / Copy Reduction.** Move descriptors,
   local overlays or copy-on-write; selected move alone is fully committed. Risk:
   medium. Every descriptor must be compared against the complete-State oracle.
3. **Stage 2G.3 — Exact Incremental Evaluation.** Only after closure proof:
   incremental timing/objective/local checker and selective Regret recomputation.
   Risk: high. Current selective recomputation is held.
4. **Stage 2G.4 — System semantic/performance regression.** Exact candidate,
   first/second, regret, RNG, action history, final State/objective plus wall,
   memory and call-count comparisons.

This ordering is evidence-driven: repeated timing/signature traversal has the
largest low-risk shared-computation surface; copy reduction follows; locality and
selective Regret remain proof-gated.
