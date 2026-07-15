# Pre-Stage-2E extended registry baseline

This read-only fingerprint treats the current engineering registry as the
future explicit `extended_mode` baseline. It uses ordered qualified names,
ordered destroy/repair lists, row-major projected pairs, and the literal mode
identifier. It does not use object addresses, `hash()`, sets, or object repr.

## Ordered destroy functions

0. `operators.random_customer_removal`
1. `operators.greedy_removal`
2. `operators.related_customer_removal`
3. `operators.route_segment_removal`
4. `operators.drone_task_removal`
5. `operators.cascade_aware_removal`
6. `operators.switch_transshipment_operator`

## Ordered repair functions

0. `operators.greedy_van_repair`
1. `operators.greedy_drone_repair`
2. `operators.best_mode_repair`
3. `operators.regret_repair`
4. `operators.cascade_repair`

## Baseline properties

- Mode identifier used in the fingerprint payload: `extended_mode`.
- Pair projection: destroy-major row-major Cartesian order, 35 entries.
- Runtime selection: two independent roulette calls, not row-major pair
  sampling.
- Destroy adaptive-weight count: 7.
- Repair adaptive-weight count: 5.
- Registry SHA-256:
  `b7f8b15d6581e3513feff1238da85e4f2aa47aa904cf727641ebd5c238100877`

## Fixed selection-only trace

Seed 42, initial weights all 1.0, twelve iterations, exactly one destroy roulette
call followed by one repair roulette call per row:

| Step | Destroy | Repair |
| ---: | --- | --- |
| 1 | cascade_aware_removal | best_mode_repair |
| 2 | switch_transshipment_operator | regret_repair |
| 3 | random_customer_removal | cascade_repair |
| 4 | cascade_aware_removal | regret_repair |
| 5 | random_customer_removal | best_mode_repair |
| 6 | related_customer_removal | cascade_repair |
| 7 | drone_task_removal | cascade_repair |
| 8 | route_segment_removal | greedy_drone_repair |
| 9 | route_segment_removal | greedy_van_repair |
| 10 | cascade_aware_removal | regret_repair |
| 11 | cascade_aware_removal | greedy_drone_repair |
| 12 | switch_transshipment_operator | cascade_repair |

Stage 2E.1 did not run, so there is no post-change fingerprint to compare.
