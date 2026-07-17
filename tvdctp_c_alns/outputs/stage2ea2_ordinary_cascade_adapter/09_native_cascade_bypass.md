# Native Cascade bypass

`cascade_aware_removal + cascade_repair` never calls the ordinary adapter.
Monkeypatch enforcement reports adapter call count zero.

Strict A.1/Stage 2D evidence remains exact:

- destroy call ID `85e5862611154e12ca70c77ed253dd4c4e0b0ee5d825033781752b690e2e7176`;
- native bundle fingerprint unchanged;
- R*, partition and dependency order unchanged;
- raw/feasible/unique strategies `6/5/4`;
- stable candidate/selection digest
  `5723032f866258bfdca59723af105deca19f9880202acd8d20e8886e1b2ea010`;
- final fingerprint
  `56db81c7cff8dc3d96bed1d7a8c7d3ebeaffb46ad3b3744f4952dc8b54c10b9e`.
