# Paper semantics versus implementation choices

| Rule | Category | Evidence / reason |
| --- | --- | --- |
| Regret-2 | Paper semantics | Uses global first and second concrete feasible strategies and `f2-f1` |
| Global first/second strategy | Paper semantics | Unified van+drone Ω(i), no mode-level compression |
| Dynamic recomputation | Paper-aligned interpretation | Every insertion changes route, carrier, feasibility, and delta context |
| Maximum regret customer | Paper semantics | Multi-candidate ranking starts with regret descending |
| Best strategy application | Paper semantics | Applies selected customer's first ranked move only |
| Single candidate priority | Implementation choice | Implementation choice: the paper does not explicitly specify this case |
| Zero candidate failure | Existing project behavior | Skip while progress exists; stop with remaining unassigned when none exists |
| Stable tie-break | Implementation choice | Implementation choice: the paper does not explicitly specify this case |
| Move identity dedup | Engineering correctness | Removes duplicate generation paths without merging equal-cost distinct strategies |
| Exact full-objective delta | Correctness requirement | Candidate copy/apply objective difference exactly matches full candidate objective |
