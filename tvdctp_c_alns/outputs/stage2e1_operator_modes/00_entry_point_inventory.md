# Entry-point inventory

Preimplementation audit was completed before `operator_modes.py` was created.

| Entry point | Current operator source before 2E.1 | Old default | Extra operators possible | Required/resulting change |
| --- | --- | --- | --- | --- |
| `main.py` | delegates to `run_c_alns()` | mutable full dictionaries | yes | CLI `--operator-mode`, default `paper_mode` |
| `build_config()` / `ALNSConfig` | no mode field | implicit full dictionaries | yes | single typed default `OperatorMode.PAPER` |
| `run_c_alns()` | `list(DESTROY_OPERATORS.keys())`, `list(REPAIR_OPERATORS.keys())` | 7 x 5 | yes | resolve/build registry once, then use its fixed name orders |
| `diagnose_calns.py` core/multiseed/long | mutates global dictionaries through `operator_set()` | caller-dependent | yes | `paper_4x4` explicit paper; `current` explicit extended |
| tests calling `run_c_alns()` | generally bypass `main.py` | full dictionaries | yes | config default now paper; extension tests must opt in |
| benchmark scripts | none present | n/a | n/a | no unresolved entry point |
| separate experiment/performance scripts | none beyond `diagnose_calns.py` | n/a | n/a | no unresolved entry point |
| RL/PPO/action-space entry | none present | n/a | n/a | no Stage 2F work |

Old destroy order: Random, Greedy, Related, RouteSegment, DroneTask, Cascade,
SwitchTransshipment. Old repair order: Local, DroneGreedy, Global, Regret,
Cascade. The old action universe was dynamically implied by dictionary insertion
order. There were three extra destroys and one extra repair. Selection was two
independent roulette calls, never pair sampling. No action ID existed. Both
diagnostics and tests could bypass `main.py`.
