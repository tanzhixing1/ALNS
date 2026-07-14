# Stage 2D versus Stage 2F boundary

| Finding | Belongs to repair or removal | Stage |
|---|---|---|
| Bundle input scope is silently replaced by all unassigned | Repair input validation/scope | Stage 2D |
| Dependency propagation covers only sortie-local relationships | Removal dependency closure | Stage 2F |
| Repair handles bundle-external unassigned customers | Repair scope | Stage 2D |
| Destroy does not record route segment/coordination snapshots | Removal output contract | Stage 2F |
| Repair expands its scope through `_finish_repair` and final cleanup | Repair behavior | Stage 2D |
| Downstream timing is not recomputed consistently | Repair/checker propagation if demonstrated | Stage 2D; no mismatch demonstrated in this audit |
| Bundle partition is same-sortie overlap plus singletons only | Removal bundle formation | Stage 2F |
| Non-cascade destroy retains stale cascade metadata | Destroy metadata lifecycle | Stage 2F |
| Repair accepts stale/incomplete metadata without validation | Repair defensive contract | Stage 2D |
| Global sortie consolidation rewrites unrelated structures | Repair finalization scope | Stage 2D |
| Missing structural relation objects prevent joint reconstruction | Removal-to-repair interface | Stage 2F prerequisite/blocker |
| Candidate strategy construction and objective ranking | Repair | Stage 2D |
| Empty joint candidate behavior | Repair policy | Stage 2D after user alignment |

## Boundary rule

Stage 2D may define a strict bundle-input interface, reject or explicitly signal missing/stale input, enumerate/select joint reconstruction strategies, preserve unrelated State, and apply passive downstream recomputation. It must not decide who belongs to `R*`, recreate the dependency closure from already-destroyed State, or redesign Cascade Removal.

Because the current removal output lacks the structural context needed by the paper's joint reconstruction, implementation is blocked until Stage 2F (or a separately approved interface stage) supplies that context.
