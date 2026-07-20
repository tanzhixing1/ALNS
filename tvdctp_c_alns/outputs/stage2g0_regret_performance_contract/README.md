# Stage 2G.0 True Regret-2 Performance Contract and Affected-Scope Audit

Status: **STAGE 2G.0 COMPLETE — STAGE 2G.1 READY — STAGE 3 HELD**.

The current frozen baseline was reprofiled at exact commit `172166ee`. The heavy
Regret call took 120.612752 s for 32,718 raw local-prefilter
attempts and 17,743 exact-scored moves. Drone work dominates
(32,514 raw). `State.copy` consumed
23.877473 s over 17,786
calls. Objective/checker requested timing almost twice per candidate, while all
17,743 candidate business States were unique.

The exact affected-scope contract has zero dynamic false negatives across van,
same/cross-van drone, high-floor, exact capacity/time-window boundary and actual
linked multi-customer/relaunch representatives. Localized checker/incremental
Regret remain held because no production certificate proves any remaining
customer unaffected.

Recommended Stage 2G.1: share one immutable derived timing/physical-route/
structural context within each exact candidate evaluation. No optimization was
implemented in this audit. Reports `00`–`19`, CSV matrices and raw measurements
contain the complete evidence.
