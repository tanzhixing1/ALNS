# Current operator registry audit

Baseline: `b886431084f1e2b8cc1db59d13f03f5798d8fa30`

The production registry is defined in `operators.py:3663-3679`. There is no
`operator_mode`, stable paper action index, or independent production paper
registry at this baseline. `run_c_alns()` reads the dictionaries in insertion
order and independently samples one destroy and one repair
(`alns_solver.py:109-147`).

## Complete current registry

| Current name | Function | Type | Paper operator | Extra operator | Current order |
| --- | --- | --- | --- | --- | ---: |
| random_customer_removal | `operators.random_customer_removal` | destroy | Random removal | No | 0 |
| greedy_removal | `operators.greedy_removal` | destroy | Greedy removal | No | 1 |
| related_customer_removal | `operators.related_customer_removal` | destroy | Related removal | No | 2 |
| route_segment_removal | `operators.route_segment_removal` | destroy | — | Yes | 3 |
| drone_task_removal | `operators.drone_task_removal` | destroy | — | Yes | 4 |
| cascade_aware_removal | `operators.cascade_aware_removal` | destroy | Cascade removal | No | 5 |
| switch_transshipment_operator | `operators.switch_transshipment_operator` | destroy | — | Yes | 6 |
| greedy_van_repair | `operators.greedy_van_repair` | repair | Local greedy repair | No | 0 |
| greedy_drone_repair | `operators.greedy_drone_repair` | repair | — | Yes | 1 |
| best_mode_repair | `operators.best_mode_repair` | repair | Global greedy repair | No | 2 |
| regret_repair | `operators.regret_repair` | repair | Regret-based repair | No | 3 |
| cascade_repair | `operators.cascade_repair` | repair | Multi-node cascade repair | No | 4 |

## Unique paper mapping

- Paper Random removal → `operators.random_customer_removal`
- Paper Greedy removal → `operators.greedy_removal`
- Paper Related removal → `operators.related_customer_removal`
- Paper Cascade removal → `operators.cascade_aware_removal`
- Paper Global greedy repair → `operators.best_mode_repair`
- Paper Local greedy repair → `operators.greedy_van_repair`
- Paper Regret-based repair → `operators.regret_repair`
- Paper Multi-node cascade repair → `operators.cascade_repair`

The mappings are unique at the public registry/function level. The diagnostic
module independently records the same four-by-four names at
`diagnose_calns.py:34-50`. No ambiguous alias or second registered
implementation maps to any of these paper roles.

## Selection, weights, and pair behavior

- Current destroy count: 7.
- Current repair count: 5.
- Potential current Cartesian combinations: 35.
- There is no stored production pair list; a pair is formed after two separate
  roulette calls (`alns_solver.py:138-147`).
- Adaptive weights, scores, and counts are separate dictionaries for destroy
  and repair (`alns_solver.py:111-116`, updates at 204-207 and 232-244).
- Pair profiling records the selected combination, but it is not a pair-level
  adaptive selector.
- Current default behavior is the full 7×5 registry because config and CLI have
  no mode field (`config.py:48-65`, `main.py:19-50`).

`diagnose_calns.operator_set("paper_4x4")` is a temporary diagnostic context
manager that mutates global dictionaries and restores them afterward. It is not
a production mode/default and supplies no compatibility guarantee.
