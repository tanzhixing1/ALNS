# Scope diff review

| File | Function | Change | Why allowed |
| --- | --- | --- | --- |
| `operator_modes.py` | mode/identity API | strict enums, constants, immutable registry, fingerprints | core 2E.1 scope |
| `config.py` | config default | typed paper default and strict builder input | unified default |
| `main.py` | CLI | canonical `--operator-mode` | explicit extension |
| `alns_solver.py` | run initialization/history | build once, filter names, action diagnostics | stable identity without sampling change |
| `diagnose_calns.py` | experiment entry | explicit paper/current mode | prevent hidden default dependency |
| `README.md` | example/documentation | document default and opt-in extension | entry audit |
| `tests/test_stage2e1_operator_modes.py` | regression | strict contract and dual-baseline tests | required evidence |
| `outputs/stage2e1_operator_modes/*` | audit | reports and CSV | required evidence |

OperatorMode added: YES. Paper/extended specs added: YES. Config/CLI defaults
changed: YES. Solver mode resolution and action diagnostics: YES.

Destroy algorithms changed: NO. Repair algorithms changed: NO. A.2 adapter:
NO. Native Cascade: NO. Ω(B): NO. Objective/checker: NO. SA/weights/formula/
initial weights/probabilities/RNG call sequence: NO. Flat sampling: NO. Action
masking: NO. Candidate generation/counts: NO. Registry in candidate loop: NO.
Silent fallback: NO. Stage 2F/PPO/RL: NO. Performance optimization: NO.
