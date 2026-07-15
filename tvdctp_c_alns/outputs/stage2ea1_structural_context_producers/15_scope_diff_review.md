# Scope diff review

| File | Function | Change | Why allowed in A.1 |
| --- | --- | --- | --- |
| `removal_structural_context.py` | immutable context records, projection/diff/fingerprint, validation and lifecycle helpers | New repair-agnostic context implementation | Explicit A.1 raw-context scope |
| `state.py` | `TVDState.copy` | Share only the frozen context instance while deep-copying all other metadata | Minimal State.copy isolation plumbing |
| `operators.py` | `_remove_customers`, four destroy entry points | Append-only observation of existing deletion effects and pre/post context finalization | Minimal producer capture wiring; selection and mutation calls preserved |
| `operators.py` | five public repair entry points | Uniform consume/cleanup decorator | Required ephemeral lifecycle boundary |
| `alns_solver.py` | `run_c_alns` | Assert persistent/current/best and returned candidates are context-free | Required ownership guard |
| `tests/test_stage2ea1_structural_context.py` | Stage 2E-A.1 regression suite | 28 focused tests covering the 23 required categories | Required A.1 verification |
| `outputs/stage2ea1_structural_context_producers/` | audit artifacts | Baselines, design evidence, test results, scope and gate decisions | Required reports |

## Protected-scope answers

| Question | Answer |
| --- | --- |
| Random selection changed | NO |
| Greedy trial/ranking changed | NO |
| Related ranking changed | NO |
| Cascade closure changed | NO |
| Cascade partition changed | NO |
| Cascade dependency order changed | NO |
| Old Cascade contract changed | NO |
| Cascade repair validation changed | NO |
| Equation (B) changed | NO |
| Global repair algorithm changed | NO |
| Global repair lifecycle boundary changed | YES — cleanup only |
| Local repair algorithm changed | NO |
| Local repair lifecycle boundary changed | YES — cleanup only |
| Regret repair algorithm changed | NO |
| Regret repair lifecycle boundary changed | YES — cleanup only |
| Cascade repair algorithm changed | NO |
| Cascade repair lifecycle boundary changed | YES — cleanup only |
| Extra registered greedy-drone repair algorithm changed | NO |
| Extra registered greedy-drone lifecycle boundary changed | YES — cleanup only |
| Objective changed | NO |
| Checker semantics changed | NO |
| SA changed | NO |
| Adaptive weights changed | NO |
| Operator selection changed | NO |
| Registry changed | NO |
| Canonical State fingerprint redefined | NO |
| Stage 2D source fingerprint changed | NO |
| `paper_mode` implemented | NO |
| Action registry implemented | NO |
| Stage 2E-A.2 work performed | NO |
| Performance optimization performed | NO |

The three ordinary-destroy/Cascade-repair combinations remain explicitly
blocked. No bundle adapter or ordinary dependency-order interpretation was
introduced.
