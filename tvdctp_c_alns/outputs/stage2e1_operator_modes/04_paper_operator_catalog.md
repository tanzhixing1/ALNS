# Paper operator catalog

Destroy order:

1. `random_customer_removal` (Random)
2. `greedy_removal` (Greedy)
3. `related_customer_removal` (Related)
4. `cascade_aware_removal` (Cascade)

Repair order:

1. `best_mode_repair` (Global)
2. `greedy_van_repair` (Local)
3. `regret_repair` (Regret)
4. `cascade_repair` (Cascade)

The names are exact current registry keys. Construction validates every key and
callable. Extras are excluded; missing members fail the whole paper registry.
