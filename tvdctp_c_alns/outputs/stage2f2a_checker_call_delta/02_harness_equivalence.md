# Harness Equivalence

Result: **CASE A — harness completely identical**.

| Evidence | Baseline | Current | Result |
|---|---|---|---|
| Test Git blob | `180150734d6273de6849c8cfd354a701defee307` | same | identical |
| Test SHA-256 | `305E9B5F668AC8F6234F38144C11DC768F325A1370956B03E81046B54B3CEFCE` | same | identical |
| `alns_solver.py` blob | `14cb1b2a6c010dd84b2230a80bd21b6549611b82` | same | identical |
| `feasibility.py` blob | `a9494e7874cc650e9af5a90f2760333a62d0e49d` | same | identical |
| `objective.py` blob | `bd94b9bc76d11a1ee7b5234d2625f516bacbb00a` | same | identical |
| `config.py` blob | `1bc29489f2019b8445f472baaac442ab8b4d7ba9` | same | identical |
| `dataset_loader.py` blob | `5aaf848ebe1bf464514e3908e280d845a93205c5` | same | identical |

Because the entire test file is byte-identical, the fixture, `_baseline_run` helper, seeds, configuration, entry, RNG instrumentation, State fingerprint helper, post-run calls, and exact expected constants are identical. The only production diff between commits is the approved Stage 2F.1 Native removal implementation in `operators.py`; the checker, objective, solver, configuration, and test accounting boundary did not change.

Runtime: Python 3.12.13, pytest 9.1.1. Exact-node runs disabled repository-wide coverage output with `-o addopts=` and disabled pytest cache/bytecode so the isolated worktrees remained clean; neither option changes test semantics.

