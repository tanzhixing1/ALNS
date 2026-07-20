# Candidate Growth Diagnosis

The 40-iteration trace completed, so these observations describe completed calls rather than a timeout extrapolation.

## Main finding

Candidate work is highly variable and concentrated in `regret_repair`. It is not a monotonic per-iteration slowdown, but individual regret calls can grow by more than an order of magnitude depending on the removed state.

- First observed regret call (iteration 6, action 6): `4,900` raw candidates.
- First call over both 30 s and 60 s (iteration 10, action 2): `32,718` raw candidates; repair `94.8849679 s`.
- Largest call (iteration 35, action 14): `58,588` raw candidates; repair `230.9850766 s`.
- Growth from 4,900 to 58,588: about `11.96x`.
- Iteration 35 candidates were dominated by drone candidates: `58,098 / 58,588`.
- Later calls became smaller again (for example iteration 40 action 14: `10,674` candidates and `37.5539 s`), disproving a simple monotonic or unbounded-growth model.

Across 40 iterations, `regret_repair` handled `178,994` raw candidates in 11 calls, compared with `18,236` for greedy-van, `19,331` for best-mode, and `262` for Cascade repair.

The largest event combines `cascade_aware_removal` with `regret_repair`, but the expensive component is the subsequent regret enumeration/scoring over the expanded removal state. Cascade repair itself and the ordinary-removal Cascade adapter were small (`0.3278 s` total and `0.0348 s` total respectively).

Conclusion: **candidate-count amplification is real and is the primary driver of the expensive calls; it is bursty, not evidence of an infinite loop.**
