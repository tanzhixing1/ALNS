# Paper Mode 80-Iteration Runtime Summary

## Command and resolved configuration

The real `tvdctp_c_alns/main.py` entry was invoked with 20 orders, 20 customers, 2 containers, 2 transshipments, 80 iterations, seed 42, `--operator-mode paper_mode`, and the requested output directory.

Resolved defaults were: `warehouse_num_vans={3: 3, 4: 3}`, `drones_per_van=2`, `max_drones_carried_per_van=3`, `high_floor_ratio=0.35`, `max_no_improve=100`, and early stop enabled. No parameter was changed.

## Outcome

| Metric | Value |
| --- | --- |
| process result | external timeout |
| tool exit code | 124 |
| external wall time | approximately 901.648 seconds |
| solver-reported runtime | unavailable |
| data-generation time | unavailable |
| initial-solution time | unavailable |
| ALNS-loop time | unavailable |
| iterations requested | 80 |
| iterations completed | unknown; not persisted before timeout |
| early-stop iteration | unavailable |
| average ALNS ms/iteration | unavailable |
| initial objective | unavailable for this process |
| best objective | unavailable |
| feasibility / violations | unavailable |
| accepted/rejected/improving/best-update counts | unavailable |

The command produced no stdout before timeout, no `paper_2c20n_iter80_seed42` result directory, and no `history.csv` or `summary.txt`. The timeout cleanup left no Python process. Consequently, runtime action counts cannot be reconstructed and are marked unavailable rather than fabricated as zero.

This is a runtime-completion/performance validation blocker. The already-passed mode/registry contracts are not reclassified as failures.

**PAPER 80-ITERATION RUNTIME VALIDATION TIMEOUT**
