# Extended mode allowlist

Extended mode contains the frozen 16 paper identities plus 19 explicitly
approved engineering pairs (35 total). IDs 16..19 add DroneGreedy repair to
the four paper destroys. IDs 20..34 cover RouteSegment, DroneTask, and
SwitchTransshipment against the five existing engineering repairs.

The allowlist is a literal tuple, not a runtime cartesian product. Paper IDs
0..15 retain the exact paper names and pair meaning. New dictionary keys are
ignored until the constant and tests are explicitly updated. Missing any
approved extended operator raises `ExtendedOperatorRegistryError`; it never
returns paper mode.
