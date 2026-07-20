# Ordinary 12-Pair Baseline Comparison

All Random/Greedy/Related pairs match the frozen Stage 2E-A.1/A.2 baseline on action ID, selection, actual-unassignment membership, repair category/status, objective, feasibility, canonical violations, business fingerprint, candidate trace where applicable, RNG digest, and lifecycle cleanup.

- Exact matches: 12/12
- Mismatches: 0
- RNG drift: 0
- Adapter drift: 0
- Context drift: 0
- `actually_unassigned` expansion: none
- Native dependency-graph production calls: 0 across all 12
- Native Path B entry: 0 across all 12

The ordinary adapter ran exactly once for IDs 3, 7, and 11, and nowhere else. It produced exact singleton membership `[12]`, `[7]`, `[12]`; it did not enlarge `actually_unassigned`. Non-Cascade repairs consumed/discarded the ordinary context without adaptation. Full comparison rows are in `03a_ordinary_12_pair_diff.csv`.

```text
ORDINARY 12-PAIR ISOLATION PASS
```
