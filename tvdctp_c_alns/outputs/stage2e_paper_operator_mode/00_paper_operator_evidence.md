# Stage 2E.0 paper operator evidence

Source: `论文-一审改稿_0424tzx.pdf`, targeted review of Figure 3,
Sections 5.1.2–5.1.5, Algorithm 1, and Sections 5.2.2–5.2.4. Page and
manuscript-line references below are the PDF's displayed page/line numbers.

| Question | Paper evidence | Conclusion | Confidence |
| --- | --- | --- | --- |
| Four destroy operators | pp. 30–31, lines 690–727 enumerate Random customer, Greedy, Related, and Cascade removal. | Four destroy operators are explicit. | HIGH |
| Four repair operators | pp. 31–32, lines 728–754 enumerate Global greedy, Local greedy, Regret-based, and Multi-node cascade repair. | Four repair operators are explicit. | HIGH |
| Pair-based action | Figure 3 text, p. 28 lines 628–632; Eq. (103), p. 36 lines 835–845: `a_t = (a_t^dest, a_t^rep)`. | RL action is a destroy/repair pair. | HIGH |
| Full 4×4 space | p. 36 lines 835–837 explicitly says all combinations of four destroy and four repair operators, yielding 16 pairs. | Full 4×4 is explicit for RL-C-ALNS. | HIGH |
| Compatibility restriction | The action section lists all combinations and no incompatible-pair rule. Algorithm 1 describes cascade removal before bundle repair, but does not state a pair restriction. | Paper unspecified. | MEDIUM |
| Action masking | No masking rule appears in the targeted action, transition, operator, or Algorithm 1 descriptions. | Paper unspecified. | MEDIUM |
| Pair order | No destroy-major/repair-major order is given. | Paper unspecified. | INSUFFICIENT |
| Action index | No numerical index-to-pair mapping is given. | Paper unspecified. | INSUFFICIENT |

## Separate conclusions that must not be conflated

- **Pair-based action:** explicit.
- **Four destroy / four repair operators:** explicit.
- **Full 4×4 RL action space:** explicit in Section 5.2.2, not merely inferred
  from `4 + 4 + pair notation`.
- **Compatibility restriction:** Paper unspecified.
- **Action masking:** Paper unspecified.

## C-ALNS versus RL selection

Section 5.1 says destroy and repair operators are adaptively selected and later
scores the destroy-repair pair (p. 29 lines 658–661; p. 33 lines 765–771). It
does not unambiguously specify whether the heuristic samples two independent
weight vectors or one pair-level vector. The current code samples destroy and
repair separately; that is an implementation fact, not a claimed paper index.

Section 5.2 is clearer: PPO selects one action whose value is a destroy/repair
pair. This audit does not implement PPO.

## Important paper/code alignment issue

Algorithm 1 (pp. 33–34, lines 773–792) performs dependency expansion, removes
associated structural snapshots, partitions the result into bundles, and then
constructs `Omega(B)`. Section 5.2.2 nevertheless declares all 16 combinations.
The paper does not explain how a non-Cascade destroy supplies the structural
bundle input consumed by Multi-node cascade repair. That missing detail must be
resolved by the code contract audit rather than assumed.
