# Reproduction Results

Exact pytest nodes were run independently in each detached worktree.

| Version | Paper node | Extended node | Checker counts |
|---|---|---|---|
| baseline `760e3bc...` | PASS | PASS | paper 909, extended 884 |
| current `9488139...` | FAIL | FAIL | paper 910, extended 885 |

Current failures were exact:

```text
paper: assert 910 == 909
extended: assert 885 == 884
```

Both instrumented repetitions reproduced the same full trace and total. Therefore:

- `BASELINE CHECKER COUNT NOT REPRODUCED`: no.
- `CURRENT CHECKER DELTA NOT DETERMINISTIC`: no.
- Delta: exactly +1 in each mode.

Only the two specified nodes and the minimum direct tracing runs were executed. No full non-medium, medium, main smoke, benchmark, Stage 2 Final Audit, or Stage 2G run was performed.

