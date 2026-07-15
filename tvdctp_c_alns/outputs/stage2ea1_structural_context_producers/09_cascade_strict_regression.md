# Cascade + Cascade strict regression

Baseline and post-change seed 29 evidence are identical:

- removed set / `R*`: `[12]`;
- native partition and dependency order: `[[12]]` / `[[12]]`;
- destroy call ID:
  `85e5862611154e12ca70c77ed253dd4c4e0b0ee5d825033781752b690e2e7176`;
- bundle fingerprint:
  `8eb99601571e8554f1c68edeaaa34f67241af5172cc7ed7bc4f47c4d56c51d9c`;
- raw/feasible/unique strategy counts: `6/5/4`;
- stable strategy-generation and selected-identity digest:
  `5723032f866258bfdca59723af105deca19f9880202acd8d20e8886e1b2ea010`;
- selected objective: `927.880274816`;
- final business fingerprint:
  `56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e`;
- final checker: feasible, zero violations;
- RNG state: unchanged by Cascade repair.

Timing diagnostics are excluded from the candidate digest. The old
`CascadeBundleSnapshot`, contract validator, candidate enumeration, Ω(B),
validation and selection code are unchanged. The raw context is a parallel
fact layer and is consumed before the existing Cascade repair body.
