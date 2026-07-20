# Focused Test Results

Runtime used:

```text
C:\Users\19088\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
pytest 9.1.1
numpy 2.3.5
```

The shell-default Python lacked pytest, and the historical project venv launcher referenced a missing Python installation. No dependency was installed; the bundled workspace runtime was used.

Final allowed focused command result:

```text
81 passed in 23.71s
```

Coverage included:

- 17 new Stage 2F.1 predicate/seed/closure/partition/atomic/boundary tests;
- 18 Stage 2D.0 Native bundle/snapshot/contract tests;
- 33 Stage 2D.1 Cascade repair boundary and atomicity tests;
- 13 selected Stage 2E-A.1 context lifecycle, Stage 2E-A.2 Native adapter bypass/ordinary isolation, action-ID 15 and Regret-isolation tests.

The first focused attempt exposed that Cascade repair validates the legacy `dependency_order_semantics` text. Production repair was not changed; Native snapshot generation retained the frozen text and the boundary tests then passed.

Per the Stage 2F.1 instruction, no full 16-pair matrix, full non-medium suite, medium suite, formal main smoke, 20/40/80 iteration run, performance test, Stage 2F.2 or Stage 2G run was executed.
