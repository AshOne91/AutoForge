# Next Task

## Next executable unit: generate the VectorStore runtime contract

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

`base_server/service/search` is now a selected AutoForge runtime service:
`tooling.search` generates provider-neutral Elasticsearch/OpenSearch health,
document, and raw-query transport with a deterministic fake and generated
ownership metadata. The next slice is `base_server/service/vectordb`: generate
the equivalent async Qdrant VectorStore contract for health and vector document
operations. Embedding, collection schema, and hybrid relevance policy remain
consumer-owned. The existing RAG overlay remains infrastructure only; the slice
must first prove the generated runtime contract before KIS adopts it.
