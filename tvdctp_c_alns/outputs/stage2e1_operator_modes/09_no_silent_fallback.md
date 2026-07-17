# No silent fallback

Focused negative tests cover invalid values, explicit `None`, missing each of
the four destroys, missing each of the four repairs, a 15-pair action table,
paper failure with extended operators still available, and extended failure
with a complete paper catalog.

Every case raises a typed error. There is no warning-and-continue path, 13/15
pair degradation, repair substitution, paper-to-extended fallback,
extended-to-paper fallback, or action ID `-1`.
