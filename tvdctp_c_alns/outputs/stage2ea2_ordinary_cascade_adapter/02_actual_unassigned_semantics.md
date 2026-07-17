# Actual-unassigned semantics

The adapter node set is exactly:

`R = post_projection.unassigned - pre_projection.unassigned = context.actually_unassigned_customer_ids`.

Validation recomputes the post fingerprint and the current destroyed-State
transition. Selected IDs, historic unassigned customers, the destroyed State's
whole unassigned list and external-boundary customers are never added.

The real anchor fixture proves the distinction: selected `{5}` produces actual
`R={5,7}`, and both customers enter one adapted bundle. The adapter leaves the
destroyed State and its `unassigned` list unchanged.
