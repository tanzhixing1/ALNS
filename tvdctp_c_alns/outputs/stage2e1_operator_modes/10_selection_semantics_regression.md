# Selection semantics regression

Original model: independently roulette-select destroy, then independently
roulette-select repair. Stage 2E.1 retains those exact two calls and only looks
up the fixed action identity after selection.

Baseline-P exact results:

- destroy/repair/pair sequences: equal;
- selection and acceptance RNG boundary digest: equal;
- accepted/rejected and feasible sequences: equal;
- objective trajectory and final fingerprint: equal;
- initial weights, scores, update formula, reaction coefficient: unchanged;
- SA temperature, probability, current/best update logic: unchanged.

Flat 16-action sampling introduced: **NO**. Action masking introduced: **NO**.
