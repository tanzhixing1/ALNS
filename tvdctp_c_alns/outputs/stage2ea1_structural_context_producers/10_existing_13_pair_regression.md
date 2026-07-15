# Existing 13-pair strict regression

Fixture: coordinated Stage 2D fixture, removal count 1, fresh seed 29 per pair.
All 13 contract-compatible pairs match the committed preimplementation
baseline exactly.

| Pair | Removed IDs equal | RNG equal | Candidate sequence equal | Selected result equal | Objective equal | Fingerprint equal |
|---|---|---|---|---|---|---|
| Random + Global | PASS | PASS | N/A (not exposed) | PASS | PASS | PASS |
| Random + Local | PASS | PASS | PASS | PASS | PASS | PASS |
| Random + Regret | PASS | PASS | PASS | PASS | PASS | PASS |
| Greedy + Global | PASS | PASS | N/A (not exposed) | PASS | PASS | PASS |
| Greedy + Local | PASS | PASS | PASS | PASS | PASS | PASS |
| Greedy + Regret | PASS | PASS | PASS | PASS | PASS | PASS |
| Related + Global | PASS | PASS | N/A (not exposed) | PASS | PASS | PASS |
| Related + Local | PASS | PASS | PASS | PASS | PASS | PASS |
| Related + Regret | PASS | PASS | PASS | PASS | PASS | PASS |
| Cascade + Global | PASS | PASS | N/A (not exposed) | PASS | PASS | PASS |
| Cascade + Local | PASS | PASS | PASS | PASS | PASS | PASS |
| Cascade + Regret | PASS | PASS | PASS | PASS | PASS | PASS |
| Cascade + Cascade | PASS | PASS | PASS | PASS | PASS | PASS |

Local/Regret stable trace digests and Cascade stable strategy digest are frozen
in `tests/test_stage2ea1_structural_context.py`; wall-clock fields are excluded.
Exact objective/fingerprint values are listed in
`00_preimplementation_baseline.md` and asserted in the focused matrix test.
