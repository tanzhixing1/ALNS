# Decisive multi-drone counterexample

The fixture uses the coordinated deterministic instance and real `TVDState`,
sortie construction, local hard-feasibility logic, move application, timing,
and canonical full checker. No monkeypatch changes feasibility behavior.

- `drone_0` and `drone_1` both initially belong to `van_0`.
- The target state leaves customer 9 unassigned.
- `drone_0` already has a real sortie that launches from `van_0` and returns to
  a terminal warehouse through `van_1`. A warehouse return ends its carried
  availability for a later van launch.
- `drone_1` remains idle on `van_0`.
- `_first_drone_for_van(state, "van_0")` returns `drone_0`.

Before the fix, the shared enumerator returned only `drone_2` candidates and
never tried `drone_1`. A manually constructed `drone_1` move passed the existing
hard-feasibility path; after applying it, the canonical checker returned
`(True, [])`.

After the fix, the same enumeration returns candidates for `drone_1` (and other
physically possible named drones); applying a `drone_1` candidate passes the
canonical checker. The returned feasible move set contains no `drone_0` target
move.

**MULTI-DRONE COVERAGE BUG CONFIRMED AND FIXED.**
