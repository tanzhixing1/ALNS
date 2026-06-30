# Codex Project Rules

- Before changing code, read `README.md` and `tests/test_regression_rules.py`.
- Do not add artificial constraints that are not present in the paper.
- Do not include `waiting_cost_reported` in `total_cost`.
- Do not treat `used_drone_sorties` as `used_drones`.
- Time windows are hard constraints; late arrival is infeasible.
- After changing code, run:

```bash
python -m pytest tests
```

- If `pytest` is not installed, say so, and at least run an equivalent smoke
  test or `python -m py_compile *.py`.
- When reporting back, always state:
  - whether `pytest` was run;
  - whether it passed or failed;
  - if it failed, the failure reason and repair status.
