# Candidate count and timing profile

Direct real Regret repair with two removed customers:

| Round | Remaining customers evaluated | Raw | Unique | Van | Drone | Enumeration seconds | Ranking seconds | Selected customer |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 52 | 52 | 12 | 40 | 0.102810 | 0.000594 | 9 |
| 2 | 1 | 34 | 34 | 7 | 27 | 0.041097 | 0.000135 | 7 |

A separate wall-clock measurement of this complete two-customer repair was 0.076145s; the last emitted trace row reported 0.075736s elapsed before the final apply/finalization tail.

Thirty-iteration deterministic ALNS profile totals:

- raw candidates: 825;
- unique candidates: 825;
- van candidates: 128;
- drone candidates: 697.

The equal raw/unique counts in these real fixtures mean the existing customer-tuple/cache-key paths already avoided duplicate structural moves before final identity dedup. The explicit duplicate-identity test confirms that duplicate records collapse while distinct equal-cost moves remain.

Full-suite runtime increased from Stage 2B's 256.99s to 455.89s. This is a reasonable correctness-first increase, not a quantity-order explosion; no candidate-space pruning was introduced.
