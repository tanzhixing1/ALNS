# Candidate identity specification

Deduplication is stable and keeps the first occurrence of each complete identity. Cost is never part of identity.

## Van identity

1. mode;
2. repaired customer;
3. van ID;
4. complete pre-insertion route tuple;
5. insertion position;
6. van home/warehouse;
7. customer container ID;
8. assigned transshipment/warehouse.

Thus two positions on the same van and equal-cost moves on different vans remain distinct.

## Drone identity

1. mode and repaired customer;
2. physical drone ID;
3. launch van, node, position, and complete launch route;
4. recovery van, node, position, and complete recovery route;
5. complete sortie customer sequence;
6. customer container ID and assigned warehouse.

The launch/recovery van fields encode same-van versus carrier-transfer/cross-van identity. Duplicate paths producing the same structure collapse to one move; equal-cost structures with any distinct identity field remain separate.
