# Main Smoke Final Evidence

The Stage 2F.2 production-entry smoke is valid on the identical baseline and was not rerun.

| Check | Default invocation | Explicit canonical `--operator-mode paper_mode` |
|---|---|---|
| exit | 0 | 0 |
| orders/customers / containers / iterations / seed | 10 / 1 / 10 / 42 | same |
| mode | `paper_mode` | `paper_mode` |
| registry fingerprint | `08a24ddd...55d71a1` | same |
| history rows | 10, readable | 10, readable |
| best objective | `811.9529412450966` | same |
| feasible / violations / penalty | yes / 0 / 0 | same |
| action IDs | `13,15,7,11,4,8,11,15,0,13` | identical |
| natural action 15 | iterations 2 and 8 | identical |
| active context leak | 0 | 0 |

Both output directories retain readable non-empty `summary.txt` and `history.csv`, plus route/load/plot artifacts. The evidence describes the result as a heuristic best objective and contains no global-optimum claim.

The noncanonical underscore spelling `--operator_mode paper_mode` intentionally fails fast in argparse. The supported hyphenated spelling succeeds; no fallback occurs.

Decision: **SMALL MAIN SMOKE PASS** and final best canonical feasibility **PASS**.
