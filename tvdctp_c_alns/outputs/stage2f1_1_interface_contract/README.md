# Stage 2F.1.1 Native Removal to Cascade Repair Interface Contract Decision

## Outcome

Decision A is approved. Stage 2F.1 corrected an invalid overlapping Native partition into legal weak-component bundles. That makes action 15 reach one existing snapshot candidate and the existing canonical validation boundary. The snapshot is field-correct; the candidate is rejected because high-floor customers in a later, explicitly allowed-unassigned bundle are still not drone-served. This is the frozen Stage 2D hard-validation behavior, followed by the frozen empty-Ψ(B) atomic failure contract.

```text
ACTION-15 CONTROL-FLOW DELTA APPROVED
VALID NATIVE BUNDLE REACHABILITY CONFIRMED
CASCADE SNAPSHOT VALIDATION CONTRACT PASS
PAPER CHECKER BASELINE 909 -> 910 APPROVED
EXTENDED CHECKER BASELINE 884 -> 885 APPROVED
STAGE 2F.1.1 COMPLETE
STAGE 2F.2 READY FOR FULL RESTART
STAGE 2G HELD
```

## Implementation

- Production changed: no.
- Exact test baselines: paper 910, extended 885.
- Assertions remain strict equality.
- Dedicated Action 15 semantic regression: added for paper and extended.
- Fallback/tolerance/performance work: none.

## Tests

- Dedicated Action 15: 2 passed.
- Stage 2F.1 focused set: 83 passed (historical 81 plus two new cases).
- Stage 2E.1 exact nodes: 2 passed.
- Direct Stage 2D boundaries: 6 passed.
- Full Stage 2F.2 and later stages: not run.

## Commit

```text
STAGE_2F11_COMMIT=172166eea9e34ae5551302d4bfa1cdb62ebc479b
tracked diff=0
staged diff=0
```

## Evidence index

- `00_git_gate.md`
- `01_action15_interface_trace.md`
- `01a_action15_interface_trace.csv`
- `02_native_bundle_contract_validation.md`
- `03_cascade_repair_consumption_contract.md`
- `04_candidate_infeasibility_analysis.md`
- `05_contract_decision.md`
- `06_implementation_or_baseline_update.md`
- `07_focused_test_results.md`
- `08_scope_diff_review.md`
- `09_gate_decision.md`

The four raw JSON traces and `action15_interface_probe.py` are retained as output-only reproducibility evidence.
