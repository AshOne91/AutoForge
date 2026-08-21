# Next Task

## Next executable unit: add HA observability search generation

Extend the ELK generator with an explicit clustered Elasticsearch selection while
preserving Filebeat's and Kibana's stable generated endpoints. Reuse the verified
search-cluster bootstrap and proxy pattern only where its lifecycle matches
observability storage. Prove one Elasticsearch member stop does not break the
generated log-ingestion/readiness path. Do not add application log-query APIs or
change consumer domain code in this unit.
