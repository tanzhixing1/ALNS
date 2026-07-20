# Scope Diff Review

## File-level review

| File | Function | Change | Predicate/MED basis | Why allowed |
|---|---|---|---|---|
| `operators.py` | Native graph helpers | Add customer-only graph, ranked edges and exact inventory | NCD-A/NCD-B; MED-2/MED-3 | Narrowly scoped to Native removal |
| `operators.py` | Native closure/partition helpers | Ordered formula-(93) closure and weak components | MED-3/MED-4 | Required Stage 2F.1 correction |
| `operators.py` | `cascade_aware_removal` | Preserve seed/RNG; precompute graph/closure/partition/snapshots; discovery-order Path B removal; exact new-membership validation | MED-1/MED-6; atomic safety | Approved Native-only scope |
| `operators.py` | `_capture_cascade_bundle_snapshot` call contract | Corrected component membership; comment labels deterministic paper-unspecified order; frozen semantics value retained | MED-5 | No schema or repair change |
| `tests/test_stage2f1_native_cascade_removal.py` | new focused tests | Predicate, rank, closure, partition, RNG, atomic and boundary coverage | Stage 2F.1 matrix | Required evidence |
| `tests/test_stage2d0_cascade_contract.py` | two legacy assertions | Compare legacy bundle membership independent of old bundle order and allow discovery-order unassigned list while preserving exact membership; retain frozen semantics text | MED-4/MED-6 | Old order is explicitly replaced by Stage 2F.1 |

## Required answers

| Question | Answer |
|---|---|
| Native seed generator changed | NO |
| Native eligible domain changed | NO |
| Native RNG call count changed | NO |
| Dependency predicate inventory added | YES |
| Customer dependency graph changed | YES |
| Non-customer nodes added to graph | NO |
| Closure control changed | YES |
| R* membership may change | YES, only for newly represented approved edges |
| Closure discovery order changed | YES |
| Removal execution order changed | YES |
| Bundle partition changed | YES |
| dependency_order semantic rule changed | NO |
| Snapshot schema changed | NO |
| Context schema changed | NO |
| Atomic removal safety added | YES |
| Ordinary destroy changed | NO |
| Ordinary adapter changed | NO |
| Cascade repair changed | NO |
| Global repair changed | NO |
| Local repair changed | NO |
| Regret repair changed | NO |
| Objective changed | NO |
| Checker changed | NO |
| State business fields changed | NO |
| State.copy changed | NO |
| compute_timing changed | NO |
| paper_mode changed | NO |
| Action IDs changed | NO |
| SA changed | NO |
| Weights changed | NO |
| Performance optimization introduced | NO |
| Top-K/beam/sampling introduced | NO |
| Fallback introduced | NO |
| Stage 2F.2 performed | NO |
| Stage 2G performed | NO |

No scope expansion was needed. `removal_structural_context.py`, snapshot/context schemas, ordinary adapter, repairs, objective, checker, State and registry sources are untouched.
