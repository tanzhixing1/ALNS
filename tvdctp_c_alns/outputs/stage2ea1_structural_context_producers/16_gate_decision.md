# Stage 2E-A.1 gate decision

| Gate | Result | Evidence |
| --- | --- | --- |
| Audit baseline committed separately | PASS | `e5d6ca16beb2dea928cbf2717352edf408d141c6` contains only the two audit directories |
| Starting tracked worktree clean | PASS | Recorded after the audit commit; tracked PDF restored to HEAD |
| Current environment test baseline established | PASS | 160-node baseline; 159 passed and one repeatable isolated 900s hang |
| RemovalStructuralContext repair-agnostic | PASS | Schema/capability validation excludes repair candidates, strategy and ordinary bundles |
| Context has no shared mutable descendants | PASS | Frozen dataclasses, tuples, frozensets and recursively frozen values |
| Pre-state projection immutable | PASS | Captured as frozen value records before business mutation |
| Mutation footprint authoritative | PASS | Computed from pre/post structural projection diff |
| External boundaries factual | PASS | Derived only from changed structural facts; counterexamples tested |
| Structural fingerprint dedicated to raw context | PASS | New projection-only SHA-256 helper |
| Canonical fingerprint unchanged | PASS | No canonical implementation change; isolation regression passes |
| Stage 2D fingerprint unchanged | PASS | No Stage 2D fingerprint change; 51 legacy tests pass |
| Context ID deterministic | PASS | Canonical serialization plus SHA-256; three independent runs per destroy |
| Algorithm RNG unaffected | PASS | Shadow equivalence and RNG-before/after assertions pass |
| Cache/business signature isolated | PASS | Active key absent from existing signature behavior; tests pass |
| State.copy safely isolated | PASS | Frozen context may share identity; all other metadata remains deep-copied |
| Random strict equivalence | PASS | Fixed-fixture shadow comparison |
| Greedy strict equivalence | PASS | Trial/ranking/output/RNG comparison |
| Related strict equivalence | PASS | Seed/ranking/output/RNG comparison |
| Cascade strict equivalence | PASS | R*, partition, dependency order, scope and contract comparison |
| Old Cascade contract unchanged | PASS | Strict Stage 2D and Cascade+Cascade regressions pass |
| Repair algorithm bodies unchanged | PASS | Only public lifecycle decorators added |
| Repair lifecycle cleanup correct | PASS | All public repair paths plus exception path tested |
| Context ownership correct | PASS | Current/best remain clean; only disposable destroyed candidate carries context |
| Persistent State context-free | PASS | Solver entry/loop/return guards and tests |
| Objective/checker unchanged | PASS | No source changes; with/without-context equivalence passes |
| Existing13 pairs unchanged | PASS | Exact removal/RNG/candidate/result/objective/fingerprint matrix |
| New3 pairs still blocked | PASS | All three fail under the unchanged old contract without pollution |
| No production action registry added | PASS | Registry/action mapping untouched |
| Deterministic | PASS | Context, footprint, destroy and repair fingerprints repeat exactly |
| Full test node collection covered | PASS | Disjoint groups cover all 188 collected nodes exactly once |
| Full regression proven | PASS | 187 nodes pass; sole baseline hang reproduced individually and not called pass |
| Scope clean | PASS | `15_scope_diff_review.md`; no A.2/paper/registry work |
| Worktree valid | PASS | `git diff --check`; exact-path staging required before commit |

The full-suite process did not finish, so this report does not claim
`FULL SUITE PASS`. The valid regression classification is
`GROUPED COMPLETE COVERAGE PASS` relative to the established baseline-B
procedure documented in `14_full_test_coverage.md`.

## Final decision

STAGE 2E-A.1 COMPLETE

STAGE 2E-A.2 READY
