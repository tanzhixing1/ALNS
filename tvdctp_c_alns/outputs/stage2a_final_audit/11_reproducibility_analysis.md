# Reproducibility Analysis

- Config reproducibility: PASS
- Instance reproducibility: PASS
- Run reproducibility: PASS
- Compared deterministic fields: config_fingerprint, instance_fingerprint, initial_state_fingerprint, initial_objective, best_objective, final_objective, accepted_candidates, infeasible_candidates, best_state_fingerprint, van_route_count, container_route_count, drone_sortie_count, best_full_feasible, operator_sequence_fingerprint
- Mismatches: none
- Runtime is intentionally excluded from equality. The seeded NumPy Generator controls operator roulette and destroy/repair randomness; all operator-sequence fingerprints match.
