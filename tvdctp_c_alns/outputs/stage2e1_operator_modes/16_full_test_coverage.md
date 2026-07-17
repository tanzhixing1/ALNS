# Full test coverage

Preimplementation known baseline: 221 collected nodes; all 220 non-medium nodes
passed; the single existing medium node exceeded approximately 901 seconds.

Stage 2E.1 adds 54 focused nodes. Final collection: **275 nodes**.

- Stage 2E.1 focused: 54 passed.
- Stage 2E.1 + A.2 + A.1 + Stage 2D focused group: 166 passed before the
  final seven entry/no-policy nodes were added; the final focused run covers all
  54 new nodes.
- Final mutually exclusive non-medium group: **274 passed, 1 deselected,
  5 expected RuntimeWarnings, 224.24 seconds**.
- Full-suite attempt: timed out after 901.2 seconds after 22 completed dots,
  at the same existing medium position, with no assertion traceback.
- Exact medium node: timed out after 901.4 seconds with no traceback.

The medium timeout is not a pass. Final conclusion:
`BASELINE-RELATIVE GROUPED REGRESSION PASS`. `FULL SUITE PASS` is not claimed.
