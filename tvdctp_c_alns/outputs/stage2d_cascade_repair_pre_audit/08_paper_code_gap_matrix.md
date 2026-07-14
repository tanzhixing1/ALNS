# Paper-code gap matrix

| Semantic item | Paper evidence | Paper meaning | Current code | Match | Classification | Stage action |
|---|---|---|---|---|---|---|
| Repair input | P32, P33-34 Algorithm 1 | `R*` partitioned into dependency bundles | Optional customer-list metadata; absent means all unassigned | NO | CONFIRMED PAPER MISMATCH | DEFER TO STAGE 2F |
| Bundle definition | P32 lines 743-746; Algorithm 1 step 8 | Customers removed together and partitioned by structural dependency | Same-sortie intersections plus singleton customers | NO | STAGE 2F REMOVAL ISSUE | DEFER TO STAGE 2F |
| Structural bundle context | Algorithm 1 steps 7, 14 | Associated route segments, sub-routes, coordination must be reconstructed | Only customer IDs survive | NO | STAGE 2F REMOVAL ISSUE | DEFER TO STAGE 2F |
| Repair scope | P33-34 | Each removed dependency bundle and associated structures | Every unassigned customer is globally completed | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Customer set | P32 lines 743-746 | Cascade-removed bundle customers | Bundle plus arbitrary external unassigned | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Processing order | Algorithm 1 “for each bundle” | Sequential bundles; exact order unspecified | Metadata order; high-floor/ID internal sort; first candidate usually consumes all | UNKNOWN | PAPER UNSPECIFIED | USER ALIGNMENT REQUIRED |
| Joint multi-node behavior | P32 Eq. (95), lines 749-753 | One joint strategy for whole bundle | Limited patterns plus sequential insertions and global completion | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Van/drone coordination | P32 lines 750-753 | Simultaneous associated route/sortie reconstruction | Mostly fixed-anchor insertion; no complete joint route reconstruction | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Candidate strategy completeness | P33-34, `Omega(B)` | Feasible joint strategy set | Four heuristic families; partial split only for size 2-3 | UNKNOWN | INSUFFICIENT EVIDENCE | USER ALIGNMENT REQUIRED |
| Objective selection | P32 Eq. (95) | Minimum full candidate objective for the joint bundle strategy | Full checker plus whole objective only after unrelated global completion | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Bundle-external unassigned | Algorithm 1 operates on `R*` bundles | No unrelated-unserved sweep described | Explicitly repaired | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Global fallback | No statement | Paper unspecified | Per-customer fallback plus final global sweep | UNKNOWN | PAPER UNSPECIFIED | USER ALIGNMENT REQUIRED |
| Failure behavior | No empty-`Omega(B)` rule | Paper unspecified | Partial return; ALNS full checker rejects | UNKNOWN | PAPER UNSPECIFIED | USER ALIGNMENT REQUIRED |
| Dynamic recomputation | Algorithm 1 steps 9-15 | Next bundle uses updated solution; within-bundle strategy joint | Recomputes after each sequential insertion, but globally | NO | ENGINEERING EXTENSION | FIX IN STAGE 2D |
| Passive downstream propagation | P31, P32 | Associated downstream feasibility must be restored | Hard checks/objective recompute timing and load | YES | MATCH | PRESERVE |
| Active unrelated served rewrite | Only associated structures are named | Unrelated structure rewrite not authorized | Global sortie consolidation can rewrite all sorties | NO | CONFIRMED PAPER MISMATCH | FIX IN STAGE 2D |
| Removal/repair boundary | P31-34 | Removal forms closure/bundles; repair reconstructs | Repair silently guesses all-unassigned scope; metadata can be stale | NO | CONFIRMED PAPER MISMATCH | DEFER TO STAGE 2F |
| Input State isolation | Engineering requirement | Candidate generation must not corrupt current solution | Top-level and candidate builders copy State | YES | MATCH | PRESERVE |

The Match column uses only `YES`, `NO`, and `UNKNOWN`; Classification and Stage action use only the required vocabularies.
