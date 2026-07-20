# Instrumentation Neutrality Gate

| Fixture | Candidate volume | first/second/regret/selection | RNG | objective/checker/violations | returned/final State |
|---|---|---|---|---|---|
| Heavy Regret | exact | exact | exact | exact | exact |
| Small Regret | exact | exact | exact | exact | exact |
| Solver | exact | exact action history | exact trajectory | exact | exact |

All six machine checks are `true`: `{'heavy': True, 'heavy_candidate_volume': True, 'small': True, 'small_candidate_volume': True, 'solver': True, 'solver_candidate_volume': True}`.

The detailed heavy observer changed Python object-allocation timing enough to
produce 2 objective cache hits versus 0 and therefore 2 fewer checker executions.
This is an existing `id(state)+signature` cache-allocation effect, not an added or
skipped logical candidate: raw/hard-feasible/unique candidate counts, every
first/second move, every regret, selected moves, RNG, result fingerprint,
objective, checker and violations remain exact. Performance call counts in this
audit therefore come from the clean production replay; observer timings are used
only for phase attribution.

Decision: **INSTRUMENTATION BEHAVIOR-NEUTRAL — PASS**.
