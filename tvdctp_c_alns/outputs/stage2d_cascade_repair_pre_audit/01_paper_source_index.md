# Paper source index

## Sources found

Only one formal paper/manuscript source exists in the repository:

| Priority | File | Type | Relevant location | Role |
|---|---|---|---|---|
| 1 | `论文-一审改稿_0424tzx.pdf` | Revised manuscript PDF, 61 pages | Sections 5.1.2, 5.1.3, 5.1.5; pages 27, 30-34; Equations (93), (95); Algorithm 1 | Authoritative paper evidence |
| 7 | `tvdctp_c_alns/README.md` | Engineering handoff | Lines 217-223 | Explicitly labels current implementation as simplified; not paper authority |

No LaTeX source, Word manuscript, supplementary cascade pseudocode, appendix implementation, or author reference code was found in the repository.

## Evidence routing

- Page 27, lines 611-620: high-level definition of cascade-aware destroy/repair and structurally dependent customer sets.
- Pages 30-31, Section 5.1.2: unserved set, dependency propagation, final removal set `R*`, associated drone sub-routes.
- Page 32, Section 5.1.3, Equation (95): bundle source, joint insertion, objective selection, constraints, coordinated reconstruction.
- Pages 33-34, Section 5.1.5, Algorithm 1: unified removal-to-bundle-to-repair data flow.
- Page 36, Section 5.2.2: action-space context; it says cascade mechanisms are embedded in destroy operators and repair operators combine insertion strategies, but it does not define the standalone Cascade repair input contract.

## Authority caveat

The project README correctly warns that the current code is a simplified engineering implementation. Its descriptions are used only to explain implementation intent. They are not used to fill gaps in the paper.
