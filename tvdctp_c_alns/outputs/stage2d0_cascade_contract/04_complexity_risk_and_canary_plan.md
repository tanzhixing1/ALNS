# Bundle-strategy complexity risk and canary plan

Stage 2D.0 implements no candidate enumeration. The paper supplies no bundle-size distribution and no evidence for exhaustive search, pruning, or a Cartesian customer-product space.

## Evidence and current fixture profile

- Paper: **No explicit bundle-size evidence was found.**
- Stage 2D.0 coordinated fixture, 100 deterministic seeds with base removal count 2: bundle-size observations `{1: 112, 2: 83}`; maximum 2.
- Bundle-count observations across those destroys: `{1: 5, 2: 95}`.
- These toy-fixture counts are not paper evidence and must not be generalized.

## Required Stage 2D.1 hard canaries

- `bundle_size`
- `affected_route_segment_count`
- `affected_drone_subroute_count`
- `raw_bundle_strategy_count`
- `unique_bundle_strategy_count`
- `state_copy_count`
- `objective_call_count`
- `checker_call_count`
- `maximum_reconstruction_depth`

Fixed fixtures may gate candidate/call counts. If diagnostics discover a per-customer Cartesian implementation, emit **CUSTOMER-COMPOSITIONAL EXPLOSION** and identify it as extended customer-compositional mode. Never silently truncate.

## Soft profile-only metrics

- `enumeration_time`
- `scoring_time`
- `bundle_repair_time`

Wall-clock values are warnings/profile data only, not fixed-second correctness gates. No top-K, beam, lossy pruning, candidate cap, or automatic fallback mode is introduced.
