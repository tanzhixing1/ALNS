# Stage 2B Local greedy audit

Final decision: **STAGE 2B COMPLETE**.

This directory contains the preimplementation audit, design and target-route rationale, Local-vs-Global evidence, focused/full test results, three-run deterministic profile, cross-van check, scope review, and final gate table for Stage 2B.

Key result: Local now chooses one deterministic target route per customer, enumerates van positions only there, restricts drone launch to that route while preserving legal cross-van recovery, and leaves scoped failures unassigned. Global default scope and all prohibited modules remain unchanged.
