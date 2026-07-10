# Unknown Violation Lifecycle

The four records are correctly rejected infeasible search candidates. Their previous Unknown label was caused by an incomplete diagnostics mapping, not by a checker false-positive or State commit error.

| ID | Iteration | Destroy | Repair | Candidate source | Customers | Local result | Full checker | Accepted | Committed | Best affected | Rollback match | True category |
| ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | cascade_aware_removal | best_mode_repair | best_mode_repair → _all_moves → _best_van_move/_best_drone_move → _apply_move → _finalize_repair | [14, 23] | van 15/70, drone 587/2253; no final whole-state local check | infeasible: late service | False | False | False | True | Timing / synchronization |

Raw checker text for record 1: `customer 14 service_start 381.344 exceeds latest 360.000.` ; `customer 23 service_start 391.287 exceeds latest 360.000.`

| 2 | 3 | switch_transshipment_operator | regret_repair | regret_repair → _all_moves → _apply_move → _finalize_repair | [6, 11, 12, 16] | van 164/714, drone 460/7895; no final whole-state local check | infeasible: late service | False | False | False | True | Timing / synchronization |

Raw checker text for record 2: `customer 16 service_start 434.487 exceeds latest 360.000.` ; `customer 6 service_start 440.147 exceeds latest 360.000.` ; `customer 12 service_start 466.837 exceeds latest 360.000.` ; `customer 11 service_start 397.108 exceeds latest 360.000.`

| 3 | 4 | route_segment_removal | greedy_drone_repair | greedy_drone_repair → _best_drone_move → _drone_insert_hard_feasible → _apply_move → optional greedy_van_repair → _finalize_repair | [6, 7, 9, 15, 16] | van 16/31, drone 650/1055; no final whole-state local check | infeasible: late service | False | False | False | True | Timing / synchronization |

Raw checker text for record 3: `customer 9 service_start 360.165 exceeds latest 360.000.` ; `customer 7 service_start 368.754 exceeds latest 360.000.` ; `customer 15 service_start 373.529 exceeds latest 360.000.` ; `customer 6 service_start 386.715 exceeds latest 360.000.` ; `customer 16 service_start 382.945 exceeds latest 360.000.`

| 4 | 9 | route_segment_removal | greedy_van_repair | greedy_van_repair → _best_van_move → _van_insert_hard_feasible → _apply_move → _finalize_repair | [13, 23] | van 21/62, drone 0/0; no final whole-state local check | infeasible: late service | False | False | False | True | Timing / synchronization |

Raw checker text for record 4: `customer 23 service_start 366.048 exceeds latest 360.000.` ; `customer 13 service_start 365.115 exceeds latest 360.000.`
