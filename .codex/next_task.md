# Next Task

## Next executable unit: verify clustered ELK member rejoin after degraded ingestion

Extend the existing opt-in clustered ELK Docker drill after the one-member outage
log ingestion. Restart the stopped Elasticsearch member, wait for three nodes and
green shard health, then search the outage-ingested record through the stable
endpoint. Preserve the observability ownership boundary; do not add repair
automation or a physical-host HA claim.
