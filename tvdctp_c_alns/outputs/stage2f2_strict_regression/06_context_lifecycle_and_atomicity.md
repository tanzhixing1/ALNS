# Context Lifecycle and Atomicity

Success-path evidence:

- persistent source/current/best fixtures started context-free;
- destroy candidates temporarily carried context;
- repair consumed or discarded context;
- every one of the 16 returned candidates, destroy inputs after boundary cleanup, and source states were context-free.

Atomic evidence:

- successful Native Path B required `newly_unassigned == R*`;
- snapshots were captured before isolated mutation;
- the focused poisoned-removal test raised `ATOMIC CO-REMOVAL CONTRACT VIOLATION`;
- caller State and metadata remained unchanged;
- no candidate, partial bundle, half-context, fallback, or reroll was returned.

Existing Stage 2D/2E atomic rollback, empty Ω(B), nested failure, stale context, and current/best lifecycle cases were included in the 81-test baseline recheck.

Result: **CONTEXT LIFECYCLE PASS / ATOMIC FAILURE CONTRACT PASS**.

