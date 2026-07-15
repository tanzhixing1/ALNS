# Context lifecycle and ownership

Storage key: `_active_removal_structural_context` in ephemeral State metadata.

Lifecycle:

1. A target destroy copies its input and explicitly discards any stale raw
   context only on that new disposable working copy.
2. It captures pre structure, runs the existing destroy, captures post
   structure, validates and attaches exactly one context.
3. A common decorator consumes the context at every registered public repair
   boundary before the repair body executes.
4. Every normal return is explicitly cleared; exception paths clear the input.
5. Solver guards assert current, best and repair-returned candidates are
   context-free before persistence/acceptance.

The old Cascade metadata is independent and remains available to Cascade
repair. Nested `greedy_drone_repair -> greedy_van_repair` consumes at the outer
boundary and the inner boundary safely sees no context.

Tests cover Global, Local, Regret, Cascade, the extra registered drone repair,
controlled exceptions, ordinary+Cascade controlled failure, current/best
ownership, stale-context replacement on a working copy and a two-iteration
solver run. No failed candidate is persisted.
