# Timing Propagation Contract

`compute_timing` rebuilds truck readiness, every active van timeline and every
sortie event, then iterates recovery-event synchronization to a fixed point.
Current production does not expose an exact local update API.

```text
modified move
  -> target route/sortie timing nodes
  -> launch/recovery synchronization constraints
  -> physical-drone location and availability
  -> cross-van recovery and later relaunch edges
  -> downstream route nodes until fixed-point closure
  -> waiting, time-window and carrier/resource checker rules
```

A van insertion cannot safely be treated as one-arc-only: the target suffix and
all connected sorties are affected. A cross-van drone insertion necessarily
couples two routes. Container/warehouse structures are not modified by Regret,
but their readiness values are immutable inputs to this candidate evaluation.
Exact incremental timing is Stage 2G.3 risk, not Stage 2G.1.
