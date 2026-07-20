# Semantic Equivalence Evidence

For the evaluated prototype:

- all three focused runs produced business fingerprint
  `741fe198e7836553136b109eb7890eef13983044aa28608c7f8b9e90745b6f45`,
  exactly matching all three baseline runs;
- the deterministic 10-iteration prefix preserved action, destroy/repair,
  acceptance, current objective, and best objective records;
- focused tests compared candidate sequence, exact score, selected result, RNG
  state, copy isolation, failure cleanup, and non-Regret isolation;
- Stage 2C True Regret-2 tests passed during the prototype evaluation.

However, Stage 2E.1 work-count canaries changed because cached evaluations were no
longer executed (`objective_calls`/`check_solution_feasible_calls`). The semantic
outputs remained equal, but the task explicitly required those regressions and
objective/checker isolation. The prototype was not accepted.

After revert, final production is byte-for-byte identical to baseline at the Git
diff level, so candidate universe/order/identity, hard feasibility, objective,
checker, first/second best, regret, selected moves, RNG, final fingerprints,
paper/extended modes, action IDs, SA, and weights retain baseline semantics.
