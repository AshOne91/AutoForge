# Next Task

## Next executable unit: Yahoo provider payload-normalization test

Add a focused KIS consumer test for the current nested Yahoo payload
normalization: title, canonical URL fallback, publication time, publisher, and
malformed-record filtering. Keep it independent of live network calls.

Do not introduce new persisted or indexed fields. A later schema change needs
recorded provider evidence and its own specification-to-generation vertical
slice.
