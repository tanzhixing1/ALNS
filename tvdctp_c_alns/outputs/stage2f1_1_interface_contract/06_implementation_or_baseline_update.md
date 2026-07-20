# Implementation / Baseline Update

Decision A was implemented without any production change.

## Exact baseline changes

- `BASELINE_P_CHECKER_CALLS`: `909 -> 910`.
- `BASELINE_E_CHECKER_CALLS`: `884 -> 885`.
- Both assertions remain strict `==` assertions.
- No range, tolerance, conditional allowance or `+/-1` behavior was introduced.
- Objective counts remain paper 653 / extended 608.
- Action histories, RNG digests, final objectives and final best-State fingerprints are unchanged.

The nearby comment records that Stage 2F.1 valid Native bundle reachability causes one existing Cascade snapshot validation and that this is an approved semantic control-flow delta.

## Dedicated Action 15 regression

`test_action15_approved_snapshot_validation_contract` is parameterized over paper and extended modes and asserts:

- valid/disjoint/exact-union Native bundles;
- pre-removal Native snapshots and matching `dependency_order`;
- exact iteration and first-bundle identity;
- exactly one raw snapshot candidate;
- exactly one `_validate_cascade_candidate` rejection;
- exact allowed-unassigned and hard-violation semantics;
- zero feasible strategies and zero objective scoring;
- no RNG mutation;
- atomic return of the destroyed business State;
- no context leakage;
- exact total checker/objective counts and unchanged final best-State fingerprint.

Modified tracked files:

- `tests/test_stage2e1_operator_modes.py`
- `tests/test_stage2f1_native_cascade_removal.py`

Committed as:

```text
STAGE_2F11_COMMIT=172166eea9e34ae5551302d4bfa1cdb62ebc479b
```
