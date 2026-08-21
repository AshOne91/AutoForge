# Next Task

## Next executable unit: verify Kibana survives an Elasticsearch member loss

Extend the existing opt-in ELK cluster Docker drill so the current singleton
Kibana `/api/status` endpoint is checked after one Elasticsearch member stops.
Keep Kibana as one instance: replica generation is deferred until a separate
Secret/TLS contract owns its shared encryption keys. Do not add application
log-query APIs or change consumer domain code in this unit.
