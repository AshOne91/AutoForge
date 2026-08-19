# Next Task

## Next executable unit: add a user-owned read-only KIS API client

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

KIS now selects the generated external-provider, distributed-lock, and
key-value-store contracts in its standalone and HA specifications. The first
consumer-owned token coordinator calls the official `/oauth2/tokenP`
client-credentials endpoint, caches a validated token before expiry, and uses a
per-credential Redis lease to prevent replica refresh storms. It is verified
only with fakes; no live credential or order execution is required.

The generic `ApplicationSpec.runtime_environments` contract is implemented and
verified: it delivers declared names to local Compose, Kubernetes Secret
references, and empty environment examples without putting values or KIS names
in AutoForge generators. Required values fail fast locally; Kubernetes requires
every declared Secret key.

The next slice declares the KIS base URL, app key, app secret, and token scope
as consumer runtime-environment names, then adds a user-owned read-only KIS API
client that obtains its Bearer token exclusively from `KisTokenCoordinator`.
Select one documented non-order endpoint only after verifying its official
request and response contract. Keep this slice free of FastAPI routes, live
requests, and all order endpoints.
