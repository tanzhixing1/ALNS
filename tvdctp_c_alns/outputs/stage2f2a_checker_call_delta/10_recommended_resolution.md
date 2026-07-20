# Recommended Resolution

## Classification

Under the audit's strict taxonomy this is **D — Semantic Control-flow Regression/Delta**, not A, B, or C.

- Not A: the State-aware sequence is not a pure inserted diagnostic check; a new raw candidate is validated, the checker result is consumed, and the action-15 returned candidate fingerprint differs from baseline.
- Not B: the harness and counting boundary are byte-identical; the extra increment occurs inside production before the profile snapshot.
- Not C: the input State has not been checked previously and the result rejects the only raw snapshot candidate. Removing the call would remove a necessary feasibility boundary.
- Not E: counts, complete sequences, State identities, caller, phase, and deterministic reproduction are established.

## Required next stage

Open a separate **Stage 2F.1.1** semantic correction/contract-decision phase focused only on the Native-removal → Cascade-repair interface for action 15.

That phase must first decide whether the current valid-bundle/one-snapshot-validation behavior is the approved Stage 2F.1 semantics. If it is approved, the semantic contract must explicitly authorize the changed action-15 candidate path before any exact-count baseline update; this audit does not authorize treating it as a diagnostic-only +1. If it is not approved, correct the Native bundle/repair interface minimally without deleting the canonical validation boundary.

After the separate correction/approval:

1. rerun Stage 2F.1 focused tests;
2. rerun both exact Stage 2E.1 nodes;
3. restart Stage 2F.2 from its Git gate;
4. keep Stage 2 Final Audit and Stage 2G held until Stage 2F.2 is fully green.

No production or test change is made in this audit.

