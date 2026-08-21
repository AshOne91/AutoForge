# Next Task

## Next executable unit: verify clustered ELK ingestion with one member stopped

Locate the existing opt-in clustered ELK Docker drill and reuse its generated
three-member Elasticsearch topology, Filebeat input, and stable proxy endpoint.
After stopping one Elasticsearch member, append a new structured log record and
confirm Filebeat indexes and search retrieves that new record through the
unchanged endpoint. Preserve the observability ownership boundary; do not add
application retries or a physical-host HA claim.
