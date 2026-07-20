# Extended-mode 5-iteration Smoke

Configuration: 20 orders, 20 customers, 2 containers, 2 transshipments, 5 iterations, seed 42, `extended_mode`.

- Exit code: `0`
- External wall time: `89.427126100 s`
- Solver-reported runtime: `86.212 s`
- Registry action count: `35`
- Registry fingerprint: `588c...6514` (full value is persisted in the generated history)
- Initial objective: `1484.4917238190928`
- Best objective: `1307.155`
- Final solution feasible: yes

Selected identities:

| Iteration | Action ID | Destroy | Repair |
|---:|---:|---|---|
| 1 | 12 | cascade_aware_removal | best_mode_repair |
| 2 | 14 | cascade_aware_removal | regret_repair |
| 3 | 33 | switch_transshipment_operator | regret_repair |
| 4 | 12 | cascade_aware_removal | best_mode_repair |
| 5 | 28 | drone_task_removal | regret_repair |

Every pair reverse-mapped to its recorded action ID in the 35-action registry. No reroll, mask, pair replacement, or paper fallback was observed.

Result: **PASS**. Extended 80 iterations were not run, as required.
