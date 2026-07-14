# Complexity canaries

Fixed coordinated two-bundle fixture, seed 29, three runs:

| Metric | Bundle 0000 | Bundle 0001 | Total/call |
|---|---:|---:|---:|
| `bundle_size` | 2 | 2 | 4 |
| `affected_route_segment_count` | 1 | 2 | 3 |
| `affected_drone_subroute_count` | 1 | 1 | 2 |
| `raw_bundle_strategy_count` | 6 | 54 | 60 |
| `unique_bundle_strategy_count` | 6 | 54 | 60 |
| `state_copy_count` | — | — | 62 |
| `objective_call_count` | — | — | 60 |
| `checker_call_count` | — | — | 121 |
| `maximum_reconstruction_depth` | — | — | 1 |

All hard counts were identical across three runs.

## Soft timings

| Run | Enumeration | Scoring | Bundle repair total |
|---:|---:|---:|---:|
| 1 | 0.117669 s | 0.010080 s | 0.129568 s |
| 2 | 0.124168 s | 0.009412 s | 0.135489 s |
| 3 | 0.092432 s | 0.008652 s | 0.103428 s |

These are profile-only values. No fixed-seconds assertion or Gate threshold exists.

## Search-shape result

- customer-compositional Cartesian product used: NO
- top-K used: NO
- beam search used: NO
- candidate truncation used: NO
- cost-based deduplication used: NO
- exact-identity deduplication used: YES
- lossy pruning used: NO

Result: PASS
