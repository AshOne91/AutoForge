# Next Task

## Next executable unit: select one KIS workload for role-specific composition

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
Alembic baseline, and raw SQL are generated and verified. The consumer-owned
writer uses the existing automation session, while a separate token-protected
internal POST requests one price and writes one snapshot. The original internal
GET remains read-only. A disposable PostgreSQL container applied the full
generated migration history and verified one generated SQLAlchemy save/read
round-trip, then was removed. A separate token-protected internal GET now reads
one snapshot by UUID through the same generated `find_by_id` contract, returns
404 when absent, and keeps database failures detail-safe.

The role-composition boundary is now bounded: generated
`environment/service-composition.json` already derives API, relay, worker,
scheduler, initializer, and infrastructure runtime roles from Compose, but
`ApplicationSpec` does not select separate application module sets for them.

The next slice must select one KIS workload that genuinely needs an independent
application role, then define only its input, lifecycle, and ownership boundary.
Do not add a generic application-role field, new deployment role, replica
policy, or generator abstraction before that workload exists. The current
market-price snapshot endpoint remains a synchronous operator API path; making
it scheduled or autonomous would be a financial-domain decision, not an
infrastructure default.
