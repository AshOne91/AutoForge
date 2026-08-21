# Next Task

## Next executable unit: verify clustered Elasticsearch member rejoin after a degraded write

Extend the existing opt-in clustered Elasticsearch Docker drill after the
one-member outage write. Restart the stopped member, wait for all three nodes and
green shard health, then search the outage-written document through the stable
endpoint. Preserve the current search contract and index ownership boundary; do
not add repair automation or a physical-host HA claim.
