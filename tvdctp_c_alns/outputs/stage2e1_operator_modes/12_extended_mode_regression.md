# Extended mode regression

Explicit extended mode reproduces Baseline-E exactly for seed 29:

- 7-destroy and 5-repair selection orders: equal;
- 12-step destroy and repair sequences: equal;
- RNG digest: equal;
- final objective `789.5462929944308`: equal;
- final fingerprint `3f8ec1b...46bbf0f`: equal;
- objective/checker calls `608/884`: equal.

This proves equivalence for the audited preimplementation engineering universe;
it does not reinterpret engineering-only operators as paper operators.
