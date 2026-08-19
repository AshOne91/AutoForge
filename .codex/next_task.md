# Next Task

## Next executable unit: validate generated token coordination in KIS

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

`base_server/service/search`, `base_server/service/vectordb`,
`base_server/service/storage`, `base_server/service/external`, and
`base_server/service/lock` are now selected AutoForge runtime services. The
external-provider and distributed-lock contracts intentionally keep KIS
credentials, token policy, and trading semantics outside generated code.

The next slice is a KIS consumer validation: inspect ownership, then compose the
generated external-provider and distributed-lock contracts around one KIS token
refresh path. The consumer must own credentials, cache record shape, refresh
policy, and domain errors. AutoForge must be corrected first if regeneration
reveals a generated-contract gap; no hand-edited generated output is a permanent
fix.
