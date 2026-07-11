# Old mode-level versus true strategy-level regret

Counterexample:

- best van strategy: 10;
- second van strategy: 11;
- best drone strategy: 30.

The previous `_all_moves` compression exposed only best van 10 and best drone 30, producing mode-level regret `30 - 10 = 20`.

True Regret-2 ranks all concrete strategies: van 10, van 11, drone 30. Therefore the first strategy is van 10, the second is van 11, and true regret is `11 - 10 = 1`.

The focused test asserts 1 and explicitly rejects 20. Consequently customer selection can change when another customer has regret between 1 and 20; the new implementation selects based on real opportunity loss rather than service-mode separation.
