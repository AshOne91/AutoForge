# Next Task

## Next executable unit: verify Redis Cluster topology after a full Compose restart

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: The generated local environment creates a six-node Redis Cluster and
the KIS scale-out check now verifies primary/replica promotion, rejoining of the
stopped primary, unchanged API container health, session reads, and a new login.

Extend the isolated generated-environment check to stop and restart the full
local profile, then confirm six-node topology, slot coverage, and application
health after the idempotent Redis initialization path runs again.

Do not add Redis Sentinel/managed Redis deployment, new session semantics, or
unrelated service orchestration in this slice.
