# Next Task

## Next executable unit: verify clustered Qdrant peer rejoin after a degraded write

Extend the existing opt-in clustered Qdrant Docker drill after the one-peer
outage write. Restart the stopped peer, wait for all three peers and the test
collection replicas to become active, then retrieve the outage-written point
through the stable endpoint. Preserve the current vector-store and collection
ownership contracts; do not add repair automation or a physical-host HA claim.
