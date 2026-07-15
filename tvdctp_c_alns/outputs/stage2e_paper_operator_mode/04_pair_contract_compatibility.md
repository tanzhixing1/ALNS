# Runtime 16-pair compatibility matrix

Fixture: the real coordinated Stage 2D fixture, one-customer removal count,
seed 29 freshly recreated for every pair. No metadata injection, monkeypatch,
wrapper, fallback, singleton conversion, or copied Cascade snapshot was used.
The diagnostic invoked the public destroy and repair functions and then the
canonical full checker. Source and destroyed input States remained unmodified
for all 16 calls.

| Action | Destroy | Repair | Public callable | Metadata contract | Semantic contract | Pair executable | Final checker | Classification |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Random | Global | Yes | Yes | Yes | Yes | Fail | B. CONTRACT-COMPATIBLE BUT FIXTURE INFEASIBLE |
| 1 | Random | Local | Yes | Yes | Yes | Yes | Fail | B. CONTRACT-COMPATIBLE BUT FIXTURE INFEASIBLE |
| 2 | Random | Regret | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |
| 3 | Random | Cascade | Yes | **No** | **No** | **No** | Fail | **C. PAIR CONTRACT-INCOMPATIBLE** |
| 4 | Greedy | Global | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |
| 5 | Greedy | Local | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |
| 6 | Greedy | Regret | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |
| 7 | Greedy | Cascade | Yes | **No** | **No** | **No** | Fail | **C. PAIR CONTRACT-INCOMPATIBLE** |
| 8 | Related | Global | Yes | Yes | Yes | Yes | Fail | B. CONTRACT-COMPATIBLE BUT FIXTURE INFEASIBLE |
| 9 | Related | Local | Yes | Yes | Yes | Yes | Fail | B. CONTRACT-COMPATIBLE BUT FIXTURE INFEASIBLE |
| 10 | Related | Regret | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |
| 11 | Related | Cascade | Yes | **No** | **No** | **No** | Fail | **C. PAIR CONTRACT-INCOMPATIBLE** |
| 12 | Cascade | Global | Yes | Yes | Yes | Yes | Fail | B. CONTRACT-COMPATIBLE BUT FIXTURE INFEASIBLE |
| 13 | Cascade | Local | Yes | Yes | Yes | Yes | Fail | B. CONTRACT-COMPATIBLE BUT FIXTURE INFEASIBLE |
| 14 | Cascade | Regret | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |
| 15 | Cascade | Cascade | Yes | Yes | Yes | Yes | Pass | A. PAIR CONTRACT-COMPATIBLE |

For Global/Local/Regret, “metadata contract Yes” means their actual required
unassigned-customer input exists; they do not require Cascade metadata. Rows
classified B reached the legitimate repair logic but this fixture's result was
rejected, so B is intentionally not treated as C.

## Required special cases

### Random → Cascade

- Public callable: Yes.
- Cascade metadata present/complete: No; all three keys absent.
- Source operator: absent; therefore not accepted.
- Real bundle snapshots / affected scope: No.
- Repair status/reason: failure — `missing cascade contract or bundle metadata`.
- Classification: C, pair contract-incompatible.

### Greedy → Cascade

Same contract result as Random → Cascade. The ordinary destroy clears prior
Cascade metadata and produces no replacement structural snapshot.

### Related → Cascade

Same contract result as Random → Cascade. Spatial relatedness does not create a
`CascadeBundleSnapshot` or structural affected scope.

### Cascade → Cascade

- All three metadata keys present.
- Contract schema version: 1.
- Source operator: `cascade_aware_removal`, accepted.
- One real bundle snapshot with real affected scope.
- Cascade repair status: success.
- Canonical checker: pass, zero violations.
- Classification: A, pair contract-compatible.

## Matrix conclusion

- Contract-compatible pairs: 13 of 16.
- Structurally contract-incompatible pairs: actions 3, 7, and 11.
- Crashed or polluted pairs: 0.
- The current code cannot truthfully expose the requested 16 valid paper
  actions without changing a protected producer or consumer contract.
