# Paper 16-Pair Contract Matrix

Fixture: Stage 2D coordinated fixture (8 customers), removal count 1, seed 29, default `paper_mode`. Every pair ran twice. Stable fields were identical in both runs. Full fields and both runs are retained in `stage2f2_pair_runs.json`; the required flat export is `02a_paper_16_pair_matrix.csv`.

| ID | Pair | Selected / actual | Context / adapter | Bundle | Cat. | Objective | Feasible | Checker / objective calls | Business fingerprint |
|---:|---|---|---|---|---:|---:|---:|---:|---|
| 0 | Random + Global | 12 / 12 | Ordinary / 0 | — | B | 40927.316361140 | no | 1 / 0 | `819471d0...9a76` |
| 1 | Random + Local | 12 / 12 | Ordinary / 0 | — | B | 40927.316361140 | no | 1 / 0 | `819471d0...9a76` |
| 2 | Random + Regret-2 | 12 / 12 | Ordinary / 0 | — | A | 926.373751792 | yes | 2 / 76 | `3f8b9bc5...c7fc` |
| 3 | Random + Cascade | 12 / 12 | Ordinary / 1 | `[12]`, order `[12]` | A | 927.880274816 | yes | 7 / 4 | `56db81c7...b9e` |
| 4 | Greedy + Global | 7 / 7 | Ordinary / 0 | — | A | 765.252317540 | yes | 1 / 9 | `da445193...e76` |
| 5 | Greedy + Local | 7 / 7 | Ordinary / 0 | — | A | 773.150287337 | yes | 1 / 9 | `95a17469...933` |
| 6 | Greedy + Regret-2 | 7 / 7 | Ordinary / 0 | — | A | 765.252317540 | yes | 1 / 101 | `da445193...e76` |
| 7 | Greedy + Cascade | 7 / 7 | Ordinary / 1 | `[7]`, order `[7]` | A | 791.639335388 | yes | 12 / 19 | `b29d4743...cb3` |
| 8 | Related + Global | 12 / 12 | Ordinary / 0 | — | B | 40927.316361140 | no | 1 / 0 | `819471d0...9a76` |
| 9 | Related + Local | 12 / 12 | Ordinary / 0 | — | B | 40927.316361140 | no | 1 / 0 | `819471d0...9a76` |
| 10 | Related + Regret-2 | 12 / 12 | Ordinary / 0 | — | A | 926.373751792 | yes | 2 / 76 | `3f8b9bc5...c7fc` |
| 11 | Related + Cascade | 12 / 12 | Ordinary / 1 | `[12]`, order `[12]` | A | 927.880274816 | yes | 7 / 4 | `56db81c7...b9e` |
| 12 | Cascade + Global | 12 / 12 | Native / 0 | `[12]`, order `[12]` | B | 40927.316361140 | no | 1 / 0 | `819471d0...9a76` |
| 13 | Cascade + Local | 12 / 12 | Native / 0 | `[12]`, order `[12]` | B | 40927.316361140 | no | 1 / 0 | `819471d0...9a76` |
| 14 | Cascade + Regret-2 | 12 / 12 | Native / 0 | `[12]`, order `[12]` | A | 926.373751792 | yes | 2 / 76 | `3f8b9bc5...c7fc` |
| 15 | Cascade + Cascade | 12 / 12 | Native / 0 | `[12]`, order `[12]` | A | 927.880274816 | yes | 7 / 4 | `56db81c7...b9e` |

All A rows have zero canonical violations. B rows share the frozen fixture timing/carrier violations recorded verbatim in the CSV/JSON. Every returned State is context-free. RNG call traces and full SHA-256 business fingerprints are in the CSV/JSON.

- A = 10
- B = 6
- C = 0
- D = 0
- A+B = 16
- Action IDs changed: no

```text
PAPER 16-PAIR CONTRACT PASS
```
