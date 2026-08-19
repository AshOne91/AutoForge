# Next Task

## Next executable unit: generate the ExternalProvider runtime contract

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

`base_server/service/search`, `base_server/service/vectordb`, and
`base_server/service/storage` are now selected AutoForge runtime services.
Search and VectorStore use provider-neutral HTTP boundaries; ObjectStorage
reuses the existing S3/MinIO environment contract and adds aioboto3 only when
selected. The next slice is `base_server/service/external`: generate a narrow
async external-provider boundary with explicit timeout, retry classification,
health, and lifecycle. It must not encode KIS credentials, token policy, or
trading business semantics. KIS token coordination will consume this boundary
with the existing Redis session and a later distributed-lock contract.
