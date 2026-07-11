# True Regret-2 design

## Complete Ω(i)

For every currently unassigned customer, Regret calls `_enumerate_feasible_van_moves` and `_enumerate_feasible_drone_moves`. Only moves passing the existing hard-feasibility functions enter Ω(i).

- Van: every legal `(van_id, insertion_position)` is retained, including multiple positions on one route and inactive routes already supplied by the existing global repair route set.
- Drone: every legal drone/customer-sequence/launch-van/launch-node/launch-position/recovery-van/recovery-node/recovery-position combination reached by the existing generator is retained. Same-van and cross-van recovery remain enabled.

No top-k, nearest-neighbor, threshold, per-vehicle compression, fixed recovery, or cross-round candidate cache is used.

## Identity and scoring

Raw feasible moves are deduplicated by complete structural identity, not cost. Each unique move is applied through `_apply_move` to a State copy and scored as:

`objective(candidate_state) - objective(base_state)`

This captures all current objective terms, including the partial-State feasibility penalty, without changing `objective.py` or the approximate costs used by existing greedy operators.

Moves are ordered by exact delta ascending, existing van-before-drone tie behavior, then stable full identity. The first two entries are the global first and second concrete strategies; regret is `second_delta - best_delta`.

## Customer choice

- Multiple candidates: regret descending, best delta ascending, original unassigned order, customer ID.
- One candidate: structured priority above every multi-candidate customer; then best delta, original order, customer ID.
- Zero candidates: preserve the previous behavior. Skip while another customer can be inserted; break and return remaining customers unassigned when no remaining customer has a move.

Implementation choice: the paper does not explicitly specify how to handle a customer with only one feasible insertion strategy.

Implementation choice: the paper does not explicitly specify zero-candidate handling or equal-regret tie-breaks; Stage 2C preserves project failure behavior and uses deterministic ordering.

## Dynamic apply loop

After selecting the highest-priority customer, Regret applies only that customer's best move through `_apply_move`. The next `while` round regenerates and reranks Ω(i) for every remaining customer on the updated State. Finalization remains the existing `_finalize_repair` path.

The optional callback trace is read-only and records round/revision, candidate counts, identities, deltas, regret, selection, enumeration/ranking time, and elapsed repair time.
