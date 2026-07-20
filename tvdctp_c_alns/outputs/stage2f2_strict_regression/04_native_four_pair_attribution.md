# Native Four-Pair Attribution

The fixed Stage 2E-A.2 matrix seed selected isolated customer 12. Its induced customer dependency graph contains no edge, so all four Native pairs retained the pre-Stage-2F.1 business baseline exactly.

| Action | Pair | Seed | R* | Discovery | Bundles | Adapter | Category | Baseline change |
|---:|---|---|---|---|---|---:|---|---|
| 12 | Cascade + Global | `[12]` | `[12]` | `[12]` | `[[12]]` | 0 | B | none |
| 13 | Cascade + Local | `[12]` | `[12]` | `[12]` | `[[12]]` | 0 | B | none |
| 14 | Cascade + Regret | `[12]` | `[12]` | `[12]` | `[[12]]` | 0 | A | none |
| 15 | Cascade + Cascade | `[12]` | `[12]` | `[12]` | `[[12]]` | 0 | A | none |

Non-trivial Stage 2F.1 double-run fixtures were also rerun:

- seed `[8]` -> edge `8→6`, R* `{6,8}`, bundle `[6,8]`;
- seed `[5]` -> edge `5→7`, R* `{5,7}`, bundle `[5,7]`;
- seeds `[8,7]` -> R* `{5,6,7,8}`, bundles `[6,8]`, `[5,7]`;
- seeds `[8,5]` -> the same R* with stable discovery order `[8,5,6,7]`.

All use only NCD-A/NCD-B, weak components, stable `dependency_order`, exact newly-unassigned membership, and zero additional RNG. Both runs of all four fixtures matched.

Unexplained Native changes: 0. Result: **NATIVE FOUR-PAIR ATTRIBUTION PASS**.
