# Stage 2E.1-P Gate Decision

## Required questions

1. **How far did the original 80-iteration timeout get?** Exact iteration is unavailable: the original 901.648-second process produced no persisted history/trace. The deterministic diagnostic completed 40 iterations in 596.05 solver seconds, and the true rerun completed all 80.
2. **What was its last destroy/repair/action?** Unavailable for the original process. In the trace, the first abnormal call was iteration 10, `random_customer_removal + regret_repair`, action 2; the largest 40-iteration call was iteration 35, `cascade_aware_removal + regret_repair`, action 14.
3. **One abnormal call or gradual slowdown?** Bursty abnormal regret calls, not monotonic gradual slowdown. Calls become smaller again after peaks.
4. **Which phase is slowest?** Repair. `regret_repair` used 573.354 of 590.952 repair seconds in the 40-iteration trace. Its nested exact scoring includes 267.308 objective seconds and 136.021 checker seconds; remaining time includes enumeration/copying/selection overhead.
5. **Cascade repair or drone enumeration?** Not Cascade repair or its adapter. Drone candidate enumeration inside regret dominates the largest call; Cascade-aware destroy can amplify the state fed into regret.
6. **Order-of-magnitude candidate growth?** Yes: 4,900 to 58,588 raw candidates (11.96x), although growth is non-monotonic.
7. **Dead-loop evidence?** No. Periodic stacks advanced through deepcopy, candidate enumeration, objective, checker, and timing paths, and all graded runs completed.
8. **Mode/registry/action lookup problem?** No. Paper rows use the strict 16-action registry and correct pair identities; extended smoke uses the strict 35-action registry.
9. **Fallback, reroll, or mask?** None observed.
10. **Should timeout be extended to complete 80?** Yes for validation, and it was completed under a 3,600-second limit. A longer timeout is not itself a satisfactory performance fix.
11. **Basis for 80-iteration estimate?** The completed 40-run took 596.05 solver seconds, initially implying about 1,192 seconds linearly; a 1,800-second estimate added headroom. The measured 80-run took 2,075.46 solver seconds and 2,776.33 wall seconds, so future unchanged runs should budget about 3,600 seconds on this machine.
12. **Separate performance stage before Stage 2F?** Yes. The evidence supports a bounded performance-repair stage focused on regret candidate enumeration/scoring and state-copy overhead, followed by identical-contract runtime validation. No such optimization was implemented here.

## Decision

```text
MODE AND REGISTRY CONTRACT PASS
RUNTIME BOTTLENECK IDENTIFIED
STAGE 2F HELD FOR PERFORMANCE DECISION
```

Although the real 80-iteration main completed successfully, its roughly 46-minute wall time is a material performance finding. This task stops here: no production fix, no Stage 2F work, and no commit.
