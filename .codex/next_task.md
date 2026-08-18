# Next Task

## Next executable unit: isolated HA RAG bootstrap completion drill

OWNERSHIP: AutoForge generated Windows bootstrap and KIS HA-profile validation.

Create a disposable, separately named HA Compose runtime with fresh volumes and
non-overlapping host ports. Start the generated RAG overlay with its inference
profile, run the generated Windows bootstrap, and verify the complete HA profile
reaches readiness after the in-network endpoint preflight. Do not reset retained
HA volumes in the normal KIS workspace: stale Patroni DCS state is an operator
recovery concern, not a reason to delete possible data. Keep the durable-worker
healthcheck as the final readiness authority; do not merge Compose projects or
make RAG mandatory for RAG-free profiles.
