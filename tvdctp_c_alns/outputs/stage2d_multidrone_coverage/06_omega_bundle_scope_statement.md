# Omega(B) implementation scope

The paper explicitly requires a bundle-level Omega(B), joint reconstruction,
full-objective selection, and coordinated vehicle/drone recovery. It does not
disclose the exact Omega(B) generation algorithm, whether every mathematically
feasible joint plan is enumerated, whether mixed splitting is allowed, or
whether dependency order may be permuted.

The implementation defines a disclosed structural Cascade neighborhood
consisting of snapshot restoration, contiguous whole-bundle van-block
reconstruction, and whole-bundle single-sortie drone reconstruction.
The paper does not disclose the exact Omega(B) generation procedure.

The current implementation does **not** actively enumerate:

- new mixed van/drone splits inside one bundle;
- placing bundle customers into different van routes;
- splitting a bundle across multiple drone sorties;
- permutations of the bundle dependency order.

Accordingly, the implementation does not claim to enumerate all feasible bundle
strategies, reproduce undisclosed author source code, or prove that the paper
requires only these three candidate families.
