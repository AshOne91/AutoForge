# Next Task

## Next executable unit: verify clustered Qdrant writes with one member stopped

Locate the existing opt-in clustered Qdrant Docker drill and reuse its generated
three-peer topology, replicated test collection, and stable proxy endpoint. After
stopping one peer, upsert a new point through the unchanged endpoint and retrieve
that same point before restoring the peer. Preserve the current vector-store and
collection ownership contracts; do not add a retry policy or physical-host HA
claim.
