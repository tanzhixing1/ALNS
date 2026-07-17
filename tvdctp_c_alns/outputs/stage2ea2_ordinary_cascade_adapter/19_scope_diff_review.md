# Scope diff review

| File | Function | Change | Why allowed in A.2 |
| --- | --- | --- | --- |
| `ordinary_cascade_adapter.py` | validation, factual edges, partition/order, snapshot/contract construction | New deterministic ordinary adapter | Sole A.2 production objective |
| `operators.py` | Cascade metadata/bundle validator | Source-aware adapted branch while preserving native branch | Adapted contract validation allowed |
| `operators.py` | `cascade_repair` public orchestration | Detach context, ordinary/native dispatch, cleanup | Required context timing and source dispatch |
| `operators.py` | external boundary projection | Public normalized wrapper used by unchanged affected-scope guard | Required external-boundary evidence |
| `tests/test_stage2ea1_structural_context.py` | existing pair matrix test | Restrict old test to its unchanged 13 pairs | A.2 now owns former three blocked expectations |
| `tests/test_stage2ea2_ordinary_cascade_adapter.py` | A.2 verification | 31 nodes cover all 36 required categories | Required regression evidence |
| `outputs/stage2ea2_ordinary_cascade_adapter/` | reports/CSV | Architecture, matrix, tests, performance and gate evidence | Required artifacts |

| Protected question | Answer |
| --- | --- |
| RemovalStructuralContext producer changed | NO |
| Random selection changed | NO |
| Greedy ranking changed | NO |
| Related ranking changed | NO |
| Cascade closure changed | NO |
| Cascade native partition changed | NO |
| Cascade native dependency order changed | NO |
| Old Cascade contract changed | NO |
| Ordinary adapter added | YES |
| Context consumption timing changed | YES |
| Cascade input orchestration changed | YES |
| Cascade Ω(B) changed | NO |
| Candidate generation changed | NO |
| Candidate scoring changed | NO |
| Tie-break changed | NO |
| Objective changed | NO |
| Checker changed | NO |
| Global repair algorithm changed | NO |
| Local repair algorithm changed | NO |
| Regret repair algorithm changed | NO |
| SA changed | NO |
| Adaptive weights changed | NO |
| Operator selection changed | NO |
| Registry changed | NO |
| `paper_mode` implemented | NO |
| Stage 2F performed | NO |
| Performance optimization performed | NO |

The user PDF commit and the two root-level `git-show` text files are unrelated
and excluded from the A.2 change set.
