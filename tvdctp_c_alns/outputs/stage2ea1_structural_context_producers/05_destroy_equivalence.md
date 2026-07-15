# Destroy strict equivalence

Fixture and golden values are recorded in `00_preimplementation_baseline.md`.
Focused test result: **28 passed** after correcting a test-only timing-digest
mistake; the final deterministic assertions exclude timing diagnostics.

| Destroy | Selection preserved | Business output preserved | RNG preserved | Context-only delta |
| --- | --- | --- | --- | --- |
| Random | `[12]` | fingerprint `994ee6...0978` | one identical choice call/state | Yes |
| Greedy | winner `[7]`, identical trial trace/ranking | `ade2fc...46eb` | consumes none | Yes |
| Related | seed `12`, order `[12,9,5,6,11,8,10,7]` | `994ee6...0978` | one identical choice call/state | Yes |
| Cascade | initial/R* `[12]`, native `[[12]]` | `994ee6...0978` | one identical choice call/state | Yes |

Random sampling, Greedy objective delta/trial order, Related distance sorting,
Cascade closure/partition/order, deletion iteration and business State mutation
were not rewritten.
