# Next Task

## Next executable unit: persist one operator-requested market-price snapshot

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
in AutoForge generators. It also declares non-secret `health_test_value` data
for the generated health test only. Required values fail fast locally;
Kubernetes requires every declared Secret key. KIS declares its base URL, app
key, app secret, and optional token scope through the contract in both profiles.

KIS now has a user-owned read-only domestic-price client that obtains its Bearer
token exclusively from `KisTokenCoordinator`. Its only endpoint is the official
current-price `GET`, and its request/response behavior is verified entirely with
fakes. The client is registered through the generated `USER_LIFESPANS` hook,
which stores it in `app.state` and closes it at shutdown without a startup
request. A user-owned internal route reuses the generated `operator` service
token, validates the stock code before I/O, and exposes only the safe price
projection. A real read-only check is present but skipped unless explicitly
enabled with `KIS_READ_ONLY_INTEGRATION=1`.

The global `automation`-store `market_price_snapshots` model, repository,
Alembic baseline, and raw SQL are generated and verified. The next slice adds a
consumer-owned persistence boundary that writes one snapshot from the existing
operator-requested read-only price result through that generated repository and
the existing automation session. Keep the endpoint internal and token-guarded;
do not add polling, a durable job, a public route, portfolio data,
order/execution, or a live KIS call.
