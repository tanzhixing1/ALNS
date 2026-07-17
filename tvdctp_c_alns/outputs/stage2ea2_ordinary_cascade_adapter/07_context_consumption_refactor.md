# Context consumption refactor

Global, Local, Regret and the extra registered drone repair keep the A.1
decorator: context is detached and discarded before their bodies run.

Cascade now owns a source-aware public boundary:

1. detach and validate the raw context;
2. copy the disposable destroyed candidate;
3. ordinary source: adapt and install ephemeral existing-contract metadata;
4. native source: bypass the adapter and retain old Stage 2D metadata;
5. run the unchanged Cascade core;
6. clear raw context and Cascade input metadata on success, controlled failure
   or exception.

The public call signature is unchanged. Current, best and returned candidates
remain context-free.
