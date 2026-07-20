# Focused Test Results

Runtime:

```text
C:\Users\19088\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
pytest 9.1.1
```

Repository-wide coverage addopts and cache writes were disabled for these narrowly scoped runs; no test semantics were disabled.

## Dedicated Action 15 interface test

```text
2 passed in 8.53s
```

Both paper and extended parameter cases passed.

## Stage 2F.1 focused set

The exact historical 81-case command from the Stage 2F.2 baseline recheck was rerun, now including the two newly collected Action 15 parameter cases:

```text
83 passed in 19.25s
```

This includes all Stage 2D.0, Stage 2D.1 and Stage 2F.1 files plus the same selected context-lifecycle, adapter-isolation, existing-pair and action-ID nodes.

## Stage 2E.1 exact nodes

Run together against one module fixture instance:

```text
tests/test_stage2e1_operator_modes.py::test_paper_search_work_matches_preimplementation_baseline
tests/test_stage2e1_operator_modes.py::test_explicit_extended_run_matches_preimplementation_baseline

2 passed in 6.58s
```

Observed exact counts: paper 910, extended 885. Objective counts remain 653 and 608.

## Direct Stage 2D boundary nodes

Six direct nodes covering pre-removal snapshot, bundle scope, empty Ψ(B)/atomic rollback, partial canonical validation, strict full checker and snapshot-not-guessing behavior:

```text
6 passed in 0.42s
```

No full Stage 2F.2, full non-medium, medium, main smoke, performance test, Final Audit or Stage 2G run was executed.

