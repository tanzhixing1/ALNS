# Stage 2D.1 Git provenance audit

Audit date: 2026-07-14 (Asia/Shanghai)

## Required command results

- `git rev-parse HEAD`: `1b3400ff329f46cc03a85b030614964553c2467c`
- `git status --short`: empty; the tracked and untracked worktree was clean before this audit output was created.
- `git merge-base 7489148 9c584a5`: `74891482523fa8a0ef15b5ef9143d3252d5250d0`
- `git merge-base --is-ancestor 7489148 9c584a5`: exit code 0.
- `git rev-parse 9c584a5^`: `74891482523fa8a0ef15b5ef9143d3252d5250d0`.
- `git merge-base 9c584a5 1b3400f`: `9c584a514a3aba68e68a7570f6741ff9979d7816`.
- `git merge-base --is-ancestor 9c584a5 1b3400f`: exit code 0.
- `git rev-list --ancestry-path --reverse 7489148..9c584a5`: only `9c584a514a3aba68e68a7570f6741ff9979d7816`.

The required full `git diff 7489148..9c584a5` was run. The repository's PDF text-conversion driver failed on the added PDF, so the audit reran the same full comparison with `--no-textconv`; it completed and showed one binary PDF plus only Markdown audit/report files. The required stat and name-status comparisons were also run for `7489148..9c584a5`, `9c584a5..1b3400f`, and `7489148..1b3400f`.

## Commit chain

```text
74891482523fa8a0ef15b5ef9143d3252d5250d0
  -> 9c584a514a3aba68e68a7570f6741ff9979d7816
  -> 1b3400ff329f46cc03a85b030614964553c2467c
```

| Commit | Parent | Files changed | Production change | Purpose | Expected |
|---|---|---|---|---|---|
| `7489148` | `0feb748` | Stage 2C Regret implementation, tests, and audit outputs (the supplied trusted Stage 2C baseline) | Yes, already covered by the supplied Stage 2C baseline | Implement strategy-level Regret-2 repair | Yes; designated baseline |
| `9c584a5` | `7489148` | 1 paper PDF; 13 files under `outputs/stage2d_cascade_repair_pre_audit/`; 1 weekly progress Markdown file | No | Commit the read-only Stage 2D preimplementation audit and its paper copy; despite the subject `Stage 2C`, its diff contains no Stage 2C or other algorithm implementation | Yes; explainable documentation/audit-only intermediate commit |
| `1b3400f` | `9c584a5` | `operators.py`, `state.py`, one Stage 2D.0 test module, and 14 Stage 2D.0 report/result files | Yes, limited to the authorized Stage 2D.0 input contract | Capture pre-removal structural snapshots, define immutable bundle-contract records/fingerprints, validate metadata freshness, clear stale Cascade metadata, and test/report those changes | Yes; matches the Stage 2D.0 declared scope |

## Why the planned baseline and actual Stage 2D.0 starting HEAD differ

`7489148` is the trusted Stage 2C algorithm baseline. Before Stage 2D.0 implementation, a separate read-only Stage 2D preimplementation audit was committed as its direct child `9c584a5`. Stage 2D.0 therefore correctly started from `9c584a5`, not by skipping or replacing the Stage 2C baseline, but because the audit/documentation commit had become the current direct descendant. There are no other commits between `7489148` and `9c584a5`.

## `7489148..9c584a5` scope classification

The full diff contains:

- added `1-s2.0-S136655452600373X-main.pdf`;
- added Stage 2D Cascade repair pre-audit Markdown files;
- added `outputs/weekly_progress/2026-07-13.md`.

It contains no production source, test, configuration, checker, objective, operator-registry, or ALNS-loop change. Consequently it introduces no unaudited algorithm behavior.

## `9c584a5..1b3400f` Stage 2D.0 scope classification

The only production files changed are `operators.py` and `state.py`:

- `state.py` adds frozen structural snapshot dataclasses, `AffectedStructureScope`, and `CascadeBundleSnapshot` canonical serialization/fingerprinting. `TVDState.copy()` semantics remain deep-copy based.
- `operators.py` adds the contract constants, business fingerprint, metadata freshness validator, deterministic destroy-call identity, pre-removal snapshot capture, and stale-metadata clearing on non-Cascade destroy/switch paths.
- `cascade_aware_removal` retains its customer selection, dependency expansion, bundle partition, and RNG call order, while capturing the structured bundle records before `_remove_customers` and attaching the contract after removal.
- The remaining changes are the dedicated Stage 2D.0 regression tests and Stage 2D.0 reports/results.

No hunk changes `cascade_repair`, its candidate builders, the canonical checker, objective implementation, ALNS main loop, Global repair, Local repair, Regret repair, operator registries, SA, or initial-solution logic. Metadata cleanup calls inside other destroy operators are the declared Stage 2D.0 metadata-lifecycle change; they do not alter customer selection or RNG behavior.

## Required answers

1. Is `9c584a5` a descendant of `7489148`? **YES; it is the direct child.**
2. Which commits lie between them? **None.** The ancestry range contains only endpoint `9c584a5`.
3. What did the intermediate endpoint commit change? **Only the paper copy, Stage 2D pre-audit reports, and a weekly progress document.**
4. Did it modify production source? **NO.**
5. Did it modify tests? **NO.**
6. Did it only modify audit reports/documents? **YES**, treating the added paper PDF as a document.
7. Is there an algorithm change not audited by Stage 2C/Stage 2D.0? **NO.**
8. Does `1b3400f` contain only Stage 2D.0-authorized snapshots, structured bundle contract, metadata lifecycle, tests, and reports? **YES.**
9. Is there a hidden change to Cascade repair, checker, objective, ALNS main loop, Global, Local, Regret, or registry? **NO.**

## Gate result

**GIT PROVENANCE PASS**

The complete ancestry is confirmed, every intervening change is explainable, there is no undisclosed algorithm change, and the Stage 2D.0 diff matches its declared input-contract scope.
