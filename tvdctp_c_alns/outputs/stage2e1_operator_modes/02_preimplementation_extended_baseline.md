# Baseline-E: current engineering universe

Captured before production edits with the complete existing 7-destroy and
5-repair dictionaries. Fixture matches Baseline-P.

- Universe: 35 implied pairs.
- Destroy order: Random, Greedy, Related, RouteSegment, DroneTask, Cascade,
  SwitchTransshipment.
- Repair order: Local, DroneGreedy, Global, Regret, Cascade.
- Destroy sequence: Random, Random, Random, DroneTask, Greedy, Related,
  SwitchTransshipment, Cascade, Greedy, RouteSegment, RouteSegment, Related.
- Repair sequence: Global, Local, DroneGreedy, Cascade, Cascade, Local,
  DroneGreedy, Cascade, DroneGreedy, Regret, Cascade, Local.
- Final objective: `789.5462929944308`.
- Final fingerprint:
  `3f8ec1b603fbb1d564063ba9a2d432148c4252af93e0e6b9305a0097f46bbf0f`.
- Objective calls: 608; checker calls: 884.
- RNG boundary-state digest:
  `57273a01c37b67814e439fbf7d5f4617e124eda6c3020aefd905f3e09f4525d5`.

All 35 old combinations are retained as an explicit approved allowlist. No
claim is made that they are paper actions; only IDs 0..15 are the frozen paper
identity table.
