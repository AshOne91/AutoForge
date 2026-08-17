# Current Status

## Stable foundation

AutoForge currently has working foundations for:

- specification and generation contracts
- manifest and file ownership
- isolated workspaces
- validation/build pipeline
- generator and validator plugins
- PostgreSQL and MySQL standalone database generation
- Redis and RabbitMQ integration foundations
- Transactional Outbox
- EventBus and ordered Pipeline execution
- durable GenerationJob processing
- PostgreSQL JobStore and worker leasing
- isolated Git checkout
- safe branch/commit/push/Pull Request automation
- authenticated Control Plane API
- persistent worker/server entry points
- GitHub webhook verification and delivery deduplication
- GitHub Actions/Jenkins validation configuration generation
- generated Dockerfile and local/integration Compose environments
- optional local PostgreSQL HA Compose mode: three Patroni PostgreSQL nodes,
  three etcd members, HAProxy writer endpoint, and idempotent logical-database
  initialization
- opt-in local RabbitMQ cluster mode: three persisted broker nodes, HAProxy at
  the unchanged `RABBITMQ_URL` endpoint, and quorum event/dead-letter queues;
  a disposable generated KIS workspace verified one-node stop, persistent
  publish through HAProxy, and broker rejoin
- PostgreSQL, MySQL standalone, Redis Cluster, RabbitMQ, migration, application, Airflow, Outbox relay,
  and durable-job worker runtime validation
- ELK and Kubernetes base-server generation
- generated ELK Filebeat collection for both `logs/*.log` and
  `logs/<service>/*.log`, with a persistent registry volume; KIS runtime
  verification confirms terminal retry errors reach Elasticsearch without replay
  after a Filebeat restart. The generated profile also ingested post-reboot
  application `/health` records into an Elasticsearch data stream; its Filebeat
  mount path is aligned with the generated integration Compose project. Central
  Elasticsearch and Kibana now use the explicit `49600`/`49601` host block.
- opt-in RAG infrastructure with Qdrant, Ollama, and one selectable search backend
  (Elasticsearch or OpenSearch), connected to generated application/worker consumers
  through an explicit external named network; both local search paths are runtime-verified.
  The KIS OpenSearch profile responds on `49460`, persists its named-volume data
  across container restart, and exposes the generated hybrid-search client path.
  With the installed `embeddinggemma` model, KIS indexed and retrieved a live
  news probe through combined keyword and vector search.
- default-generated, profile-selected MinIO S3-compatible local storage with
  idempotent backup-bucket bootstrap; generated Compose and an actual MinIO
  backup round trip are runtime-verified
- optional RAG, MinIO, and ELK long-running services now generate
  `restart: unless-stopped` plus service-specific health checks; persistent
  Qdrant/search/Ollama/MinIO/Elasticsearch/Filebeat state remains on named
  volumes, while one-shot initialization containers stay non-restarting. A
  disposable generated runtime verified RAG Qdrant/OpenSearch/Ollama recovery,
  MinIO recovery and marker persistence, and Elasticsearch/Kibana/Filebeat
  recovery with Elasticsearch index persistence. Qdrant uses an image-native
  Bash TCP probe because its minimal image has no curl; Filebeat healthchecks
  allow the generated bind-mounted config permissions.
- ELK central and standalone collector overlays now use Compose-file-relative
  defaults that resolve `LOG_ROOT` and `FILEBEAT_CONFIG` to the generated
  project root in both documented launch modes.
- Identity/Session/Sharded Profile and Scheduled Ingestion input Blueprints
- Yahoo provider failure boundary: positive timeout and timeout/provider error
  classification with preserved causes; KIS schedules bounded durable retries
  (three total attempts, delayed through the generated Outbox contract) and logs
  an operator-visible structured error when retries are exhausted
- KIS terminal retry logs are queryable in Elasticsearch by `event_type`,
  `job_id`, `run_key`, `attempt`, and `max_attempts`
- generated KIS durable-job endpoints are runtime-verified for Bearer-token
  authentication, idempotent `(job_type, run_key)` requests, `automation` store
  routing, and status retrieval; generated Airflow uses those endpoints rather
  than an in-process timer
- KIS durable `news_collection` followed its generated `news_index` job through
  the running worker and indexed ten Yahoo articles into OpenSearch with the
  configured embedding model
- KIS host validation now has the declared `yfinance` dependency; the full
  consumer pytest suite passes (`33 passed`) with the documented
  `-p no:cacheprovider` command, so the Windows ACL warning is avoided without
  changing repository configuration
- KIS Ruff validation passes and the declared package builds successfully as
  both wheel and source distribution using the local build tool
- The generated KIS wheel installs into a fresh virtual environment and
  imports successfully as `kis_auto_trading` version `0.1.0`
- A separate KIS runtime image tag builds from the generated Dockerfile and
  returns `/health` HTTP 200 with the real database and Redis lifespan
  connections on the existing integration network
- The wheel-verified image also passes a disposable Compose replacement check:
  three application replicas became healthy and returned `/health` 200 without
  changing the long-running Compose project
- A disposable Nginx front-end routes to those three replicas: six proxied
  `/health` requests returned 200, request IDs round-tripped, and the rendered
  config contains the forwarded-client headers and upstream proxy contract
- A real Nginx request's `X-Request-ID` is persisted in the host JSON log; after
  restarting one application replica it remained present and all replicas plus
  Nginx returned healthy
- After that restart, a new proxied `/health` record was ingested exactly once
  into the Elasticsearch `filebeat-*` data stream with its request ID intact
- The declared observability endpoints are live: Elasticsearch `49600` returns
  cluster health and the existing record, while Kibana `49601` redirects to
  `/app/home` with HTTP 200
- `ProjectSpec` now rejects overlapping generated host-port offsets across
  local services, RAG, object storage, and central ELK; the full AutoForge suite
  passes (`486 passed, 6 skipped`) and the KIS specification regenerates cleanly
- generated durable Jobs can cancel only before worker claim: cancelled messages
  remain harmless when delivered because the worker's atomic claim skips their
  handler; KIS verifies API cancellation idempotency and the worker boundary
  against local PostgreSQL, the Outbox relay, RabbitMQ, and the live worker
- KIS scale-out integration also runs the generated Airflow DAG against the
  live token-protected API; DAG discovery is verified and its wait task turns
  a cancelled Job into a controlled failure without invoking a handler
- `scripts/verify_scale_out.py` automates the Airflow cancellation assertion
  together with the PostgreSQL, RabbitMQ, Redis Cluster, and two-API checks
- The default generated local environment separates `airflow-init`,
  `airflow-webserver`, and a long-running `airflow-scheduler`; KIS validates
  actual scheduler task execution in an isolated generated Compose project. It
  waits for scheduler DAG registration, unpauses the isolated DAG, triggers one
  historical logical date, confirms the Durable Job through the live API, and
  cancels it before worker claim. The generated test project uses port block
  `59400` and removes only its own containers, network, and volume. External
  news-provider calls and a production schedule remain unverified.
- The opt-in `airflow_scheduler_replicas: 2` profile is runtime-verified in an
  isolated generated KIS environment using PostgreSQL HA. Both indexed
  schedulers became healthy; after stopping one, the survivor scheduled a DAG
  whose trigger task succeeded. The matching `(job_type, run_key)` produced one
  durable Job, and the stopped scheduler rejoined healthy. The Job's business
  handler remains intentionally unimplemented in that generated fixture, so its
  wait task retried after the successful trigger; this does not weaken the
  scheduler or idempotency result. See
  [ADR-0001](../docs/adr/0001-local-airflow-scheduler-ha.md).
- KIS's full RabbitMQ outage-recovery check verifies that a profile update
  committed during a broker outage is published after RabbitMQ recovery and
  processed exactly once by the `kis.profile.events` consumer; repeated delivery
  preserves one Inbox record.
- KIS terminal retry alert policy currently uses the structured Elasticsearch
  signal as the operator-facing baseline; external webhook/email/SMS delivery
  remains deferred until a destination, payload boundary, and delivery
  guarantee are explicitly selected
- KIS validation slice: Yahoo Finance news collection → PostgreSQL canonical records
  → durable `news_index` handoff → selectable search-backend indexing is runtime-verified

## Docker work

The optional Dockerfile Generator and generated-project daemon build are verified.
Local/integration Compose and Kubernetes base manifests are generated under their
own contracts. Artifact publishing, live deployment, and cloud credentials are not
owned by the Dockerfile Generator.

Generated Compose reuses its application image tag. Runtime verification therefore
rebuilds the image after consumer source changes. Redis Cluster nodes advertise
Compose service hostnames and the idempotent initializer reintroduces persisted
nodes through their current Compose addresses before checking topology; this
recovers six-node Redis topology after a full Docker network recreation without
resetting unrelated services or Redis volumes.

The opt-in `tooling.single_host` Generator produces a generated Compose operating
overlay for a declared local application environment. KIS generation verifies the
generated Nginx public entry point, three application replicas, restart policy,
and configurable host log mount merge cleanly with the generated integration
Compose profile. An isolated KIS Compose drill verifies Nginx `/health`, exactly
three healthy application replicas, and recovery through the proxy after one
application container is restarted. Host backup/bootstrap procedures remain
unverified.
The single-host specification now supports the explicit
`windows_task_scheduler` bootstrap provider and generates a PowerShell script
that reruns the named Compose project with `up -d --wait`; task registration and
host reboot execution remain operator-level verification. On the Windows host,
the task was registered successfully, the script started the generated
49400/49410/49430/49431/49440 profile, all declared services became healthy, and
Nginx returned `GET /health` with HTTP 200. A real Windows reboot then restarted
the same profile and returned HTTP 200 through Nginx again. This verifies the
selected Windows bootstrap path on one host, not physical-host failure recovery.
After the reboot drill, an application replica was restarted again; its
container returned healthy, the host log file count remained stable, and the
persisted per-process JSON file contained `application stopping`,
`application starting`, and successful health-request records.

The generated Kubernetes profile currently selects two Nginx proxy replicas and
three application replicas, but both counts are specification values rather than
architectural constants. Kubernetes exposes independent `proxy_replicas` and
`application_replicas` settings; the single-host Compose profile exposes
`application_replicas` and intentionally keeps one Nginx owner for its one public
host port. Its basic readiness and liveness probes use `/health`; explicit
SIGTERM/preStop draining, KIS OAuth token coordination, and multi-node log
persistence remain unverified. A Docker Desktop Kubernetes check applied the
generated profile, observed 2/2 proxy and 3/3 application readiness, returned
`GET /health` through a temporary port-forward, and recovered one replaced Pod
from each Deployment. This is a single-node validation, not multi-node HA proof.
The Kubernetes Nginx template forwards `X-Real-IP`, `X-Forwarded-For`, and
`X-Forwarded-Proto`.

KIS runtime verification confirms the generated PostgreSQL HA mode elects one
leader with two streaming replicas, exposes the existing `postgres:5432` writer
contract through HAProxy, and promotes a replacement leader after the active
leader is stopped. The stopped node rejoins as a replica. This is a single-host
Docker integration topology; it does not claim multi-host, Kubernetes, backup,
or managed-database production HA.
`kis-auto-trading/scripts/verify_generated_postgres_ha.py` repeats that check in
an isolated Compose project and removes only its own containers, network, and
named volumes. The same check starts the generated FastAPI application, verifies
its Compose healthcheck and `GET /health`, stops the active Patroni leader, and
confirms that the unchanged application container becomes healthy again after
HAProxy promotes a replacement writer. This is a local failover recovery check;
it does not claim every in-flight request is transparently retried.

The same isolated check restarts all six generated Redis nodes, reruns the
idempotent cluster initializer, verifies `cluster_state:ok`, three primaries,
three replicas, all 16,384 slots, and recovers the unchanged application
container. It also recreates the full Compose network, starts the three Patroni
nodes in their intentional leaderless state, explicitly selects a fixed
candidate, and verifies manual Patroni failover, HAProxy writer recovery, and
the unchanged application's health. This is a bounded local operator-recovery
check; it does not select a production candidate automatically or claim zero
data loss.

The KIS scale-out integration profile reserves Redis Cluster's fixed
`172.29.0.10`–`172.29.0.15` addresses and allocates other containers from
`172.29.0.128/25`. This keeps partial service restarts from colliding with Redis
node addresses.

Generated local Compose marks long-running PostgreSQL, Redis, RabbitMQ,
application, relay, worker, and Airflow services with restart policies. The
durable-job worker policy is explicitly configured by
`ApplicationSpec.durable_job_worker_restart_policy` and defaults to
`unless-stopped`. The generated worker healthcheck now verifies an actual
RabbitMQ connection using the existing `aio-pika` dependency, while migration
and initial RabbitMQ readiness remain dependency-gated. KIS live Compose
verification reaches `healthy`, and a RabbitMQ restart leaves the worker
healthy without a worker restart. One-shot migration and initialization
services remain non-restarting. The generated outbox relay also verifies its
RabbitMQ connection; KIS live verification reaches `healthy` and reconnects
after a broker restart under `restart: unless-stopped`. Host Docker auto-start
and AWS Launch Template UserData remain deployment concerns outside the
disposable integration profile. KIS live verification also keeps the generated
application HTTP healthcheck healthy across a PostgreSQL restart; that endpoint
now also probes internal PostgreSQL and Redis reachability. Redis Cluster mode
uses `require_full_coverage=True`, `PING`, and a multi-node startup list. KIS
live verification reports a six-node cluster with three primaries, three
replicas, all 16,384 slots, and stable healthy checks. Stopping `redis-7000`
promotes its replica `redis-7004`; the cluster stays `cluster_state:ok` with
zero failed slots and the generated application stays healthy. Restoring 7000
returns it as a replica of the promoted primary. A direct KIS probe still fails
while PostgreSQL is stopped and succeeds after recovery. The probe does not
authenticate SQL commands or validate external managed stores.

The KIS scale-out verification also records both API container IDs before a
Redis primary failure. After replica promotion, both unchanged API containers
remain Compose-healthy and answer `GET /health`; existing-session reads and a
new login still pass. The stopped Redis primary is restarted during cleanup so
the shared profile is not left degraded; the verification also waits for that
node to rejoin as a replica of the promoted primary and rechecks API health.

The generated durable-job and Outbox repositories support a caller-supplied
availability time, so consumer retries can be delayed without changing an event's
original occurrence time.

The KIS legacy scale-out Compose profile now applies `restart: unless-stopped` to
all long-running PostgreSQL, Redis, RabbitMQ, API, worker, and Airflow services.
Its worker RabbitMQ-connection checks and scheduler job check are live. A host
restart exposed missing long-running-service restart policies; the persisted
services were then recreated without volume reset, and the focused scale-out
verification passed Airflow job paths, RabbitMQ Outbox recovery/DLQ/idempotency,
Redis primary promotion and rejoin, and two-API session/shard behavior. This
legacy profile still uses one RabbitMQ broker and one Airflow scheduler, so it
is not broker or scheduler HA.

The port-collision guard was also checked with explicit, non-default overrides:
an application block at `49300`, RAG at `49400`, and central ELK at `49600`
validate successfully. Reusing `49400` for the application and ELK blocks is
rejected by `ProjectSpec` before generation. The KIS Compose defaults resolve to
the non-overlapping application/PostgreSQL/RabbitMQ block (`49400`/`49410`/
`49430-49431`). The specification guard validates these declared values; a
manually colliding runtime `.env` override is a deployment-time input and is
not independently revalidated by `ProjectSpec`.

The generated Windows single-host bootstrap now runs a read-only
`docker compose config --format json` preflight and rejects duplicate published
host ports before `up`. The KIS generated bootstrap matches the generator output;
its current integration configuration passes the preflight with five published
ports.

An intentional disposable Compose configuration with two services publishing
`49999` was rejected by the same preflight before any `up` call. The complete
AutoForge suite now reports `489 passed, 6 skipped` with the cache provider
disabled.

The generated Windows bootstrap was then executed against the live KIS profile:
all three application replicas and Nginx reached `healthy`, the proxy returned
`GET /health` `200`, and `COMPOSE_IGNORE_ORPHANS=true` suppressed the expected
warning from the separately managed ELK Compose project without removing it.

The registered `AutoForge-kis-auto-trading-bootstrap` Task Scheduler job was
also triggered manually. It completed without changing the existing healthy
stack; Nginx and all three application replicas remained healthy and `/health`
returned `200`. A physical host reboot remains an operator-controlled check.
The read-only verbose task query confirms an `At logon time` trigger, the
expected PowerShell action, `Interactive only` logon mode, and last result `0`.
After the reboot, application `/app/logs` still mapped to the host
`C:\kis-auto-trading\logs` bind mount, where recent per-container log files
remained present with non-zero sizes.

No backup automation is currently implemented. The consumer guide now defines a
safe single-host drill: copy the host log bind mount and create a PostgreSQL
custom-format dump outside the project, then restore only into a disposable
target and verify its checksum/tables.

The first live backup drill copied the host logs and created non-empty custom
format dumps for `identity`, `account_shard_1`, and `account_shard_2` under a
timestamped directory outside the repository. Each dump received a SHA-256
checksum. The Compose `postgres` service is HAProxy, so the guide targets the
`postgres-ha-0` database node for `pg_dump`.

The `identity` dump was restored into a uniquely labeled disposable vanilla
PostgreSQL container after excluding source-specific extension, ACL, and
`metric_helpers` archive entries; two core public tables were verified and the
container was removed. A complete restore still requires a target with the same
Spilo extensions and roles. Binary dumps are now copied with `docker cp` rather
than PowerShell stdout redirection, which would corrupt custom-format archives.

The same `identity.dump` was then restored successfully into a disposable
`ghcr.io/zalando/spilo-16:3.3-p3` target using `--clean --if-exists
--no-owner --no-privileges`; six public tables were verified and the labeled
container was removed.

`account_shard_1.dump` was restored with the same source-compatible procedure;
eight public tables were verified and its labeled disposable container was
removed.

`account_shard_2.dump` completed the same drill with eight public tables
verified. All three generated database artifacts have now passed a disposable
Spilo restore check; no live database was overwritten.

The single-host baseline audit is complete: durable named/bind volumes, rotated
file logs, health checks, bootstrap/reboot recovery, and disposable backup/
restore evidence are all present. Off-host backup automation, retention policy,
and managed storage remain outside the current baseline.

`autoforge.core.backup.BackupArtifact` now provides the typed manifest boundary
for future adapters. It validates relative artifact names, non-negative sizes,
timezone-aware UTC timestamps, and 64-character SHA-256 checksums.
`autoforge.core.backup.BackupTransfer` now defines the minimal async `put` and
checksum `verify` seam; no provider SDK or credential implementation is bundled.
`autoforge.core.backup.S3StorageConfig` now validates an HTTP(S) endpoint,
bucket, normalized prefix, and paired credential references without storing
secret values.
`BackupTransfer.configuration` now connects that validated target configuration
to each provider implementation without introducing an SDK.
The client boundary is now explicitly provider-injected; no S3 SDK dependency is
part of the core package yet.
`S3CompatibleBackupTransfer` now provides the first infrastructure adapter with
manifest-size validation and delegated remote verification.
The concrete client choice is `aioboto3` via the optional `backup` dependency
extra; it is not part of the default installation yet.
`Aioboto3S3Client` now provides the lifecycle-safe wrapper with lazy import,
runtime secret resolution, and object metadata checksum verification.
The MinIO integration check skips without configured external service credentials
and passed against a disposable local MinIO container; unit tests continue to use
injected fakes.
`StorageSpec` now generates the local MinIO overlay by default while preserving
an explicit disable switch and the Compose `storage` execution profile.
`S3StorageConfig.from_environment` now connects the generated `S3_*` settings to
the provider-neutral backup contract without storing credential values in core.
The `autoforge backup` preflight command now builds one artifact manifest,
transfers it through the existing S3 adapter, and verifies the remote checksum.
KIS input specifications were generated into a disposable consumer workspace;
its generated MinIO profile created the default bucket and the actual preflight
uploaded and verified an artifact through the host endpoint.
The KIS single-host generated README ownership conflict is resolved: common
port guidance now comes from AutoForge, while the KIS-specific Spilo backup
drill lives in its user-owned local integration operations document.
`tooling.local_environment.database_provider` owns runtime selection and defaults
to PostgreSQL; logical database schemas remain portable. The implemented MySQL
slice generates `mysql:8.4`, named storage, `mysql-init`, `asyncmy` DSNs, and a
MySQL baseline. A disposable runtime check confirmed initialization, application
user access, generated raw DDL application, and generated schema persistence
across restart. A generated-project Docker build then installed the MySQL
authentication dependency, ran `migrate` successfully against MySQL 8.4, and
verified the Alembic version plus `login_accounts` table.
The MySQL HA slice is implemented and runtime-verified: `mysql_mode: ha`
generates a three-member MySQL 8.4 InnoDB Cluster, a signed official MySQL
Router 8.4 image, Router-backed `mysql:6446` DSNs, application-account
initialization, migration, and generated-schema verification. It remains local
process-level resilience; its disposable verifier stops the initial primary,
confirms an idempotent Router-backed write through the promoted primary, then
restarts and verifies the stopped node rejoined. Provider-selected production
deployment is not implemented. The existing Kubernetes base-server generator
continues to consume database URLs through `secretKeyRef`; it does not generate
MySQL cluster resources. A focused generator contract test verifies that this
boundary remains true when the same specification enables local MySQL HA, and
the generated Kubernetes README explains the same provider-owned boundary. The
generated application starts and retains its
`/health` contract throughout that failover verification. PostgreSQL-specific
messaging/Durable Jobs remain excluded from the MySQL profile. The published
`mysql/mysql-router:8.0` image remains incompatible with MySQL 8.4 writer
routing and is not generated.

## Development tooling

Repository navigation and cost-control tooling is maintained through:

- `AGENTS.md`
- `.agents/skills/`
- Serena
- code-review-graph
- Ponytail LITE

Detailed tool procedures belong in Skills, not in `.codex` reference documents.

## Verification policy

Use focused tests first.
Run broader integration or full-suite tests only when the change risk warrants it.
