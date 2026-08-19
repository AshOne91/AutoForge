# Next Task

## Next executable unit: declare user-owned application runtime environments in the specification

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

The coordinator is deliberately not registered in FastAPI yet. Before a
containerized KIS client can consume it, AutoForge needs one generic,
spec-declared application runtime-environment contract: named required or
optional variables must flow into generated local Compose, Kubernetes Secret
references, and generated environment examples without hard-coding KIS names
in a generator. Prove that contract in a disposable generated workspace and
then declare the KIS URL, app key, app secret, and scope through it.

Only after that contract is verified should the next slice add a user-owned,
read-only KIS API client that obtains its Bearer token exclusively from the
coordinator. Select one documented non-order endpoint only after its official
request/response contract is verified. Do not add a FastAPI route, live request,
or order endpoint in the same unit.
