# Next Task

## Next executable unit: register the read-only KIS client in the application lifespan

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
every declared Secret key. KIS declares its base URL, app key, app secret, and
optional token scope through the contract in both profiles.

KIS now has a user-owned read-only domestic-price client that obtains its Bearer
token exclusively from `KisTokenCoordinator`. Its only endpoint is the official
current-price `GET`, and its request/response behavior is verified entirely with
fakes.

The next slice registers that client as a user-owned FastAPI lifespan dependency
with explicit shutdown. It may construct configuration and shared clients but
must not make a KIS request during startup. Keep it free of a public route,
background polling, account access, and all order operations.
