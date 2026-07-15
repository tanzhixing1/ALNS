# Stage 2E compatibility gate decision

| Gate | Result | Evidence |
| --- | --- | --- |
| Paper four destroy evidence | PASS | PDF pp. 30–31, lines 690–727 |
| Paper four repair evidence | PASS | PDF pp. 31–32, lines 728–754 |
| Pair-based action evidence | PASS | Figure 3 and Eq. (103) |
| Full 4×4 evidence | PASS | PDF p. 36 lines 835–837 explicitly says 16 pairs |
| Compatibility restriction evidence | PARTIAL | Paper unspecified; no restriction or implementation contract given |
| Action masking evidence | PARTIAL | Paper unspecified |
| Paper operator mapping unique | PASS | `01_current_registry_audit.md` |
| Static producer-consumer contract | FAIL | Only Cascade destroy produces valid Cascade snapshots |
| Random + Cascade contract | FAIL | Missing contract/bundle metadata |
| Greedy + Cascade contract | FAIL | Missing contract/bundle metadata |
| Related + Cascade contract | FAIL | Missing contract/bundle metadata |
| Cascade + Cascade contract | PASS | Real schema/source/bundle; repair and checker pass |
| All 16 pair contracts valid | FAIL | 13 valid, actions 3/7/11 incompatible |

All Stage 2E.1 mode/default/registry/action-index gates are **NOT RUN** because
the mandatory Stage 2E.0 compatibility gate failed. No `operator_mode`, action
mapping, default-entry change, fallback, masking, or reduced action space was
implemented.

## Stage status

- Stage 2D: **FINAL CLOSED**
- Stage 2E.0 compatibility audit: **COMPLETE**
- Stage 2E implementation: **BLOCKED**

## Final decision

**STAGE 2E BLOCKED BY OPERATOR CONTRACT**

This is the required result for a real structural incompatibility, not a test
failure. Stage 2F, Stage 3, and RL/PPO were not entered.

## User decision options for a separate stage

### Option A — General structural snapshot contract

Make every destroy produce a real common destroy→repair structural snapshot so
all four can legally invoke Cascade repair. This changes non-Cascade destroy
output contracts and requires a separate paper-alignment audit without changing
their selected customer sets.

### Option B — Contract-compatible paper pairs only

Use fewer than 16 actions. This conflicts with the current explicit user target
and needs paper evidence for a compatibility restriction; Codex cannot silently
change 16 to 13.

### Option C — Keep 16 indices with action masking

Mask the three incompatible pairs. The paper does not disclose masking, and the
static/dynamic mask semantics would affect future PPO design. It cannot be
introduced silently in Stage 2E.

### Option D — Reinterpret Cascade repair

Construct bundles from an ordinary removed-customer set. This risks replacing
the Stage 2D structural Cascade semantics with guessed information and cannot be
done without new paper evidence and a dedicated contract stage.

Suggested next stage: **Stage 2E-A — Paper Action-space and Operator-contract
Alignment**.
