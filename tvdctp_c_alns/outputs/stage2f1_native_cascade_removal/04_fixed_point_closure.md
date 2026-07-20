# Ordered Fixed-point Closure

The implementation initializes `discovered_set` and `discovery_order` from RNG-returned seed order. The set is used only for membership. A cursor traverses `discovery_order`; each newly reachable target is appended once in the graph's stable neighbor order.

Properties verified by focused tests:

- one-hop and multi-hop propagation;
- cycles terminate through membership tracking;
- self-loops and duplicate edges do not duplicate customers;
- multiple seeds and multiple chains all propagate;
- multi-source merges are deduplicated;
- isolated seeds remain in `R*`;
- no depth cap, probability, feasibility cutoff, reroll or fallback;
- graph/closure consumes zero RNG.

This implements formula (93)'s monotone fixed point (**PAPER EXPLICIT**) with an ordered worklist (**APPROVED MINIMAL ENGINEERING DECISION**).

## Stage 2F.0 fixture results

| Fixture | Seed order | Discovery trace | R* membership | Discovery/removal order | Pairwise deterministic |
|---|---|---|---|---|---|
| single_cross_van_chain | 8 | 8→6 | 6,8 | 8,6 | yes |
| same_sortie_duplicate_membership | 5 | 5→7 | 5,7 | 5,7 | yes |
| two_dependency_chains_two_bundles | 8,7 | 8→6; 7→5 | 5,6,7,8 | 8,7,6,5 | yes |
| two_seed_two_chain_order | 8,5 | 8→6; 5→7 | 5,6,7,8 | 8,5,6,7 | yes |
