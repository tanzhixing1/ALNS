# Objective and Checker Profile

The 40-iteration Stage 2E.1-P trace recorded:

- Objective: `86,425` calls, `26` existing cache hits.
- Canonical checker: `88,312` calls, `279` existing cache hits.
- `compute_timing`: `174,432` calls, `26,009` cache hits.
- State signature construction: `349,207` calls, `47.31762595591135 s` total.

For the focused iteration-10 Regret call, transparent business-key observation found `26` duplicate objective evaluations and `1,215` duplicate checker evaluations. The larger timing redundancy is structural: objective computes timing, timing normalizes candidate fields, and checker can look up the same State using the normalized signature rather than the signature under which timing was initially stored.

The evaluated repair-local prototype therefore:

1. retained exact objective/checker results;
2. cached exact objective and canonical-checker results by the deterministic business signature only inside one Regret invocation;
3. recorded computed timing under both its pre- and post-normalization signatures during that invocation, so the checker reused the exact timing that objective had just computed;
4. cleared all local namespaces in `finally`, including failure paths.

The prototype preserved the focused result fingerprint, candidate records, and exact
results, but reduced median wall time by only `6.775417849251609%` and combined
actual objective/checker evaluations by only `3.468354430379747%`. It also required
changes inside `objective.py` and `feasibility.py`, contrary to the requested
objective/checker source-isolation canary. The prototype was therefore rejected and
fully reverted. No approximate objective, skipped checker, relaxed feasibility
condition, cross-repair/run cache, or accepted production change remains.
