# Next Task

## Next executable unit: verify clustered OpenSearch writes with one member stopped

Reuse the existing opt-in clustered RAG search Docker drill for the generated
OpenSearch backend rather than duplicating the Elasticsearch scenario. Create a
one-replica test index, stop one OpenSearch member, then write and search a new
document through the unchanged `RAG_SEARCH_URL` proxy contract. Preserve the
provider-neutral search and index ownership boundaries; do not add application
retries or a physical-host HA claim.
