# Unknown Classification

- Unknown classification: PASS
- Local feasibility alignment: PASS
- Candidate apply/commit integrity: PASS

All four record-level Unknown entries are hard customer time-window violations. `_record_customer_service` records `service_start > latest`; the full checker correctly rejects the final candidate. Local checks operate per insertion and there is no final whole-state local checker after a multi-insertion repair/finalization, so these final infeasible candidates are permitted search outcomes. They were not accepted or committed, and rollback fingerprints match.
