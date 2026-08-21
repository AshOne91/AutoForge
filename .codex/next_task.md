# Next Task

## Next executable unit: verify clustered Elasticsearch writes with one member stopped

Locate the existing opt-in clustered Elasticsearch Docker drill in the RAG
generator tests and reuse its generated three-member topology, test index, and
stable proxy endpoint. After stopping one member, index a new document through
the unchanged endpoint and retrieve it through search before restoring the
member. Preserve the current search contract and index ownership boundary; do
not add application retries or a physical-host HA claim.
