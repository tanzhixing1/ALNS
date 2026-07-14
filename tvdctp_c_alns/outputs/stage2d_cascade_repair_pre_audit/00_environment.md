# Environment and audit scope

- Audit: Stage 2D Cascade Repair pre-implementation, read-only alignment audit
- Audit date: 2026-07-14 (Asia/Shanghai)
- Repository root: `D:\STUDY\game\github-program\noteread\ALNS`
- Project root: `D:\STUDY\game\github-program\noteread\ALNS\tvdctp_c_alns`
- Required baseline: `74891482523fa8a0ef15b5ef9143d3252d5250d0`
- Actual HEAD before audit: `74891482523fa8a0ef15b5ef9143d3252d5250d0`
- Commit subject: `feat: implement strategy-level regret-2 repair`
- Bundled Python: 3.12.13
- Paper SHA-256: `F63ADCEC894459C958A7EF4DCDB7F280672C1D34DB00764BCDD386175C5188F8`

## Worktree guard

Before the audit, `git status --short` contained only the pre-existing untracked directory:

```text
?? tvdctp_c_alns/outputs/weekly_progress/
```

That directory was not read as authoritative paper evidence and was not modified. No production source, tests, config, checker, objective, registry, or ALNS-loop file was changed. The only new files produced by this audit are under `outputs/stage2d_cascade_repair_pre_audit/`.

## Read-only verification performed

Focused existing tests:

```text
tests/test_stage2c_regret2.py::test_cascade_does_not_call_regret_candidate_enumerator
tests/test_regression_rules.py::test_drone_sortie_consolidation_merges_feasible_same_anchor_sorties

2 passed in 5.41s
```

Full pytest was not rerun in this audit because the request permits necessary focused tests and prohibits implementation work. The Stage 2C baseline's prior full-suite result remains separate historical evidence, not a result of this audit.

Three in-memory diagnostic probes were run without creating or modifying project code:

1. Bundle `[5, 6]` plus bundle-external unassigned customer `7`: `cascade_repair` returned `unassigned=[]` and served customer `7`.
2. Unrepairable bundle `[5]`: `cascade_repair` returned `[5]` still unassigned and the full checker rejected the result.
3. After one cascade cycle, a later non-cascade destroy retained stale `cascade_bundles=[[7, 10]]`; it did not clear the metadata.

Both success and failure probes confirmed the input State was unchanged; `cascade_repair` starts from a deep State copy.
