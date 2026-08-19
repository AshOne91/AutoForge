# Next Task

## Next executable unit: generate the Redis distributed-lock runtime contract

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

`base_server/service/search`, `base_server/service/vectordb`,
`base_server/service/storage`, and `base_server/service/external` are now
selected AutoForge runtime services. The external-provider contract keeps KIS
credentials, token policy, and trading semantics outside generated code while
providing the narrow async transport path they will use.

The next slice is `base_server/service/lock`: generate a Redis distributed-lock
boundary suitable for coordinating KIS token refresh across replicas. It must
provide explicit ownership, TTL-based acquisition/release, deterministic fake,
and lifecycle without adding KIS-specific credentials or global state. The
consumer will retain token cache shape, refresh policy, and KIS business rules.
