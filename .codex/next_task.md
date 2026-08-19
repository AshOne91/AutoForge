# Next Task

## Next executable unit: build the first KIS Open API token-coordinator slice

The default standalone profile and generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The generated `service-composition.json` exposes stable
API, relay, worker, scheduler, initializer, and infrastructure roles.

`base_server/service/search`, `base_server/service/vectordb`,
`base_server/service/storage`, `base_server/service/external`, and
`base_server/service/lock`, and `base_server/service/cache` are now selected
AutoForge runtime services. The external-provider, distributed-lock, and
key-value-store contracts intentionally keep KIS credentials, token policy, and
trading semantics outside generated code.

KIS currently has Redis session and Yahoo-news integrations but no KIS Open API
OAuth token implementation. The next slice must therefore create the first
consumer-owned KIS token coordinator, using the generated external-provider and
distributed-lock contracts only after their generated ownership is selected in
the consumer specification. It must use the official KIS API contract, keep
credentials out of source control, and prove cache/lease behavior with a fake;
live credentials or order execution are not prerequisites. AutoForge must be
corrected first if regeneration reveals a generated-contract gap; no hand-edited
generated output is a permanent fix.
