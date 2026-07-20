# Performance Acceptance Contract

## Semantic hard gate

For every fixed fixture compare exact candidate identities, hard-feasible set,
unique business States, per-customer first/second, Regret, selected customer/move,
RNG state, objective, canonical checker, violations, returned State fingerprint,
solver action history and final best. Reuse the frozen floating-point comparison
rules; no new tolerance is allowed. Any mismatch is immediate revert.

## Required performance measurements

Report heavy Regret wall; solver wall and Regret P50/P90/P95; candidate throughput;
State.copy count/time; timing/objective/checker/signature count and inclusive/
exclusive time; absolute peak working-set/private memory.

## Predeclared merge thresholds

- Stage 2G.1: at least 15% median heavy-call wall reduction and at least 20%
  reduction in actual timing/signature derived-work executions; solver median at
  least 10% better; peak private memory no more than 10% higher.
- Stage 2G.2: at least 20% heavy-call wall reduction or 40% State.copy-time
  reduction; peak private memory no more than 10% higher.
- Stage 2G.3: threshold declared per exact subfeature before implementation, never
  below 15% on its target fixture, with zero oracle mismatch.

Use at least 3 clean repetitions and compare medians on the same machine/process
protocol. If semantic Gate fails, benefit is below threshold, P95 regresses by
more than 10%, or memory exceeds the bound: **REVERT OR DO NOT MERGE**.
