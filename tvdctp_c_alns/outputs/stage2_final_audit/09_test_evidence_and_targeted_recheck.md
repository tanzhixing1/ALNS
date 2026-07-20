# Test Evidence and Final Targeted Recheck

## Reused complete Stage 2F.2 evidence

Reuse is valid because HEAD remains `172166eea9e34ae5551302d4bfa1cdb62ebc479b`, tracked/staged diffs were empty, and the frozen production/test blobs match that baseline.

- collected: 294;
- non-medium: 293 passed, 1 deselected, 5 existing warnings, 68.77 s;
- medium: 1 passed, 397.85 s;
- combined disjoint coverage: 294/294 passed;
- Stage 2D groups: 18 + 40 passed;
- Stage 2E groups: 28 + 33 + 54 passed;
- Stage 2F file: 19 passed;
- failed nodes: none.

The roughly 398-second medium node was not rerun, as the final-audit contract explicitly permits reuse on the identical clean baseline.

## Final targeted recheck

Bundled runtime: Python 3.12.13, pytest 9.1.1. Repository coverage addopts and pytest cache writes were disabled only for this narrow command; collection/test semantics were not filtered or modified.

Coverage included:

- paper default/legacy behavior, frozen orders, exact 16-action Cartesian registry;
- exact Stage 2E.1 paper and extended search-work nodes (910/885 checker expectations);
- the complete 19-node Stage 2F.1 file, including predicate/closure/partition/seed/membership, Action 15 paper+extended, and Path B atomic failure;
- ordinary adapter lazy isolation;
- all four parameter cases of public repair context consumption;
- one maximum-Regret customer/application semantic node;
- one Local no-global-fallback semantic node.

Result:

```text
31 passed in 18.16s
failed = 0
```

Decision: **FINAL TARGETED RECHECK PASS**. No test, fixture, expectation, or production file was edited.
