# Determinism analysis

Three independent 30-iteration runs used the same code, generated instance, seed 42, configuration, and `run_c_alns` entry point.

All runs matched on:

- initial objective: 637.594910064123;
- best objective: 619.802720191427;
- final/current objective: 708.028468056919;
- 18 selected-customer events and their complete sequence;
- every traced best/second move identity, delta, and regret (`semantic_trace_hash=dab8008371f54fbe0445`);
- candidate counts: 825 raw, 825 unique, 128 van, 697 drone;
- 29 accepted and 1 infeasible ALNS candidates;
- best State fingerprint: `68da68ee6a1645917f8f`;
- final checker: feasible with no violations.

Elapsed-time fields were intentionally excluded from semantic equality because they are diagnostic wall-clock measurements and do not affect decisions.
