# Stage 2C impact

Stage 2C single-customer Regret uses the repaired shared drone enumerator. Its
ordering and regret calculation were not changed.

The focused regression constructs the real unavailable-first/available-second
state, invokes `_enumerate_regret_moves()` for the target customer, and confirms
that a feasible non-first `drone_1` move survives. Existing Stage 2C tests pass.

There is no new fallback, approximation, top-K, beam, or altered Regret-2
tie-break. The only impact is complete named-drone coverage before the existing
feasibility and scoring logic.
