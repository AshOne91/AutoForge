# Next Task

## Next executable unit: generate the ObjectStorage runtime contract

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

`base_server/service/search` and `base_server/service/vectordb` are now selected
AutoForge runtime services. `tooling.search` generates provider-neutral
Elasticsearch/OpenSearch transport; `tooling.vector_store` generates Qdrant
readiness and point/query transport. The next slice is
`base_server/service/storage`: generate an S3-compatible ObjectStorage runtime
boundary by reusing the existing `StorageSpec`, MinIO overlay, and provider
neutral backup/S3 configuration where their contracts already fit. Do not create
a duplicate storage client or add a cloud SDK to the default runtime. Object
keys, bucket lifecycle, retention, and domain document layout remain
consumer-owned.
