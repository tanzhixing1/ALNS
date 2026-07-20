# Stage 2E.1-P Runtime Bottleneck Diagnosis

Status: **complete**.

```text
MODE AND REGISTRY CONTRACT PASS
RUNTIME BOTTLENECK IDENTIFIED
STAGE 2F HELD FOR PERFORMANCE DECISION
```

The strict mode/registry contracts passed, all 10/20/40 diagnostic grades completed, and the gated true 80-iteration production main completed. The bottleneck is bursty `regret_repair` candidate enumeration and exact scoring, especially drone-dominated candidate sets; no deadlock, fallback, reroll, mask, or action-identity defect was found.

## Required artifacts

- `00_git_gate.md` — baseline/cleanliness gate
- `01_invalid_mode_check.md` — fail-fast invalid mode result
- `02_extended_5iter_smoke.md` — strict 35-action extended smoke
- `03_probe_design.md` — read-only instrumentation design and probe incident disclosure
- `04_10iter_trace.jsonl` — flushed 10-iteration event trace
- `05_20iter_trace.jsonl` — flushed official 20-iteration event trace
- `06_40iter_trace.jsonl` — flushed 40-iteration event trace
- `07_operator_timing_summary.csv` — operator/phase aggregates
- `08_action_timing_summary.csv` — all 16 paper action aggregates
- `09_candidate_growth.md` — candidate-count analysis
- `10_timeout_stack_trace.txt` — periodic stacks plus preserved initial native-handler incident
- `11_main80_runtime_summary.md` — true production 80-run outcome
- `12_gate_decision.md` — answers to all required questions and final gate

Supporting raw console logs, the temporary probe, generated extended-smoke outputs, and generated `paper_main_80` outputs are retained in this directory. The original timed-out run's exact iteration and last pair are explicitly reported as unavailable rather than inferred.

No production source, test, or configuration semantics were changed. No Git commit was created. Stage 2F was not started.
