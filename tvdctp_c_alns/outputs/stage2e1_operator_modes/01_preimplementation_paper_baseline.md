# Baseline-P: paper 4 x 4

Captured before production edits by temporarily restricting the existing
dictionaries to the four paper destroys and four paper repairs. Fixture:
10 customers, data seed 42, ALNS seed 29, 12 iterations, early stop disabled.

- Destroy sequence: Random, Random, Greedy, Random, Related, Cascade, Cascade,
  Related, Related, Related, Greedy, Random.
- Repair sequence: Regret, Global, Global, Cascade, Global, Local, Cascade,
  Global, Regret, Cascade, Global, Regret.
- Accepted: `T,F,T,T,T,F,F,T,T,F,T,T`.
- Final objective: `789.5462929944308`.
- Final cache/business fingerprint:
  `9de8f7ba48e3e29c3d7853e257c3515f9c86b4749cc4ce0d0493e051465fe583`.
- Objective calls: 653; checker calls: 909.
- Destroy calls: 12; repair calls: 12.
- RNG boundary-state digest:
  `0ef1b46c0559070d2546d0261ec49177635ed842cdeb4b5fb8820c671da5bf3b`.
- Feasible: yes; violations: none.

Candidate/objective/checker profiles, per-iteration candidate/current/best
objectives, acceptance decisions, RNG states, and final weights were captured.
The 12-iteration fixture precedes the 50-iteration update boundary, so every
final weight remains 1.0; `_update_weights`, scores, and reaction formula were
left byte-for-byte unchanged by Stage 2E.1.
