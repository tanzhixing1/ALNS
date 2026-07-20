# Stage 2G Readiness and Exact-Equivalence Contract

Decision: **STAGE 2G READY** on input baseline:

```text
BASELINE_COMMIT=172166eea9e34ae5551302d4bfa1cdb62ebc479b
```

Stage 2G is authorized for performance work only after branching from this exact manifest. It must preserve in `paper_mode`:

- 4×4 catalog, action IDs 0–15, registry fingerprint and default mode;
- complete unique True Regret-2 candidate semantics;
- exact first/second move, regret values, selected customer and selected move;
- objective/checker/timing results and canonical feasibility decisions;
- destroy/repair RNG calls, call order, roulette/SA trajectory, and action history;
- context ownership, Native bypass, R*, bundles, Path B, atomic failures;
- final State fingerprint and objective for fixed seeds;
- all 294 regression nodes, the final targeted gate, and equivalent smoke evidence.

No approximation is permitted in paper mode. Any sampling, truncation, top-K, beam, approximate delta, or trajectory-changing cache policy must be explicit **EXTENDED-MODE ONLY** and cannot reuse the paper-baseline claim.

Recommended gates, without choosing an implementation here:

1. **2G.0** — affected-range and exact performance-contract audit;
2. **2G.1** — candidate representation and `State.copy` cost work;
3. **2G.2** — safe shared timing/objective/checker computation;
4. **2G.3** — exact incremental Regret and selective recomputation;
5. **2G.4** — semantic equivalence, measured benefit, deterministic trajectory, full regression.

This report decides readiness only. It contains no cache, optimization implementation, performance claim, PPO/RL work, tag, or commit.
