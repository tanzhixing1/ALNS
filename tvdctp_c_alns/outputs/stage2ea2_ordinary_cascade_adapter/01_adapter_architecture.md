# Ordinary Cascade adapter architecture

The adapter is an objective-free bridge from the immutable A.1 fact model to
the existing `CascadeBundleSnapshot` type:

`RemovalStructuralContext → validation → actual-R → atomic edges → connected components → structural topological order → CascadeBundleSnapshot`.

It does not enumerate candidates, call the checker/objective, select a repair,
expand R or invoke another repair. `operators.cascade_repair` installs the
adapted snapshots as ephemeral existing Cascade metadata and then calls the
unchanged `_enumerate_bundle_reconstruction_strategies` Ω(B) path.

No second repair contract or snapshot hierarchy was introduced.
