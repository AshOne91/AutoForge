# Current Status

## Stable foundation

- generated database schema evolution now supports explicit additive module
  revisions after an immutable scaffolded `0001` baseline. A revision may add a
  declared nullable/defaulted column or create declared tables in one store;
  generated Alembic and raw SQL keep those changes in `0002+` files. AutoForge
  does not infer live-database diffs. Focused DDL/Alembic tests and the full
  suite pass. KIS adopts the contract for SignalEvent: its original `0001`
  baseline remains unchanged, while generated `0002` adds optional producer
  expiry and the global per-subscription `SignalDeliveryIntent` persistence
  boundary. KIS materializes one deterministic pending intent per enabled
  subscription through the existing Outbox/Inbox transport before expiry. An
  operator-token-protected, read-only KIS endpoint lists pending global intents
  by domestic stock code without exposing subscription-management data. KIS
  still has no external delivery channel.
- State-changing endpoints can opt into a separate Redis-backed request replay
  contract with `EndpointSpec.idempotency`. Generated routes require an
  `Idempotency-Key`, fingerprint the method/path/body, atomically claim the
  namespaced key with a bounded TTL, replay completed JSON responses, reject
  conflicting reuse, and release failed claims. KIS `update_profile` is the
  first consumer opt-in; generated HA output and the request contract validate
  cleanly. An isolated Docker drill with two API replicas proved one in-flight
  winner, a 200 replayed response, and 409 conflicting-key rejection through
  Nginx; the disposable stack was removed afterward.
- KIS now provides two verified record-to-search handoffs over the same
  transport: canonical `NewsArticle.source_key` values are carried by a
  durable `news_index` job and projected by the consumer-owned
  `NewsSearchIndexer` into `news-articles-v1`; `DurableJobRecord.job_id` values
  are projected separately by `DurableJobHistorySearchIndexer` into
  `operator-durable-jobs-v1` with a payload-safe summary. Both use the existing
  Elasticsearch/OpenSearch keyword-plus-vector transport while retaining
  domain-specific fields and relevance policy. AutoForge owns only the
  optional RAG infrastructure and environment contract; it does not yet
  generate a domain projection or a second search API.
- KIS now persists generated `SignalEvent` records in the global `automation`
  store; signals carrying a producer-owned expiry emit `signal.created` through
  a dedicated queue. Its Inbox consumer reads the enabled global subscription
  projection and saves one deterministic pending intent per eligible
  subscription before expiry, without calling an external channel. Authenticated users
  manage their own domestic-stock `SignalSubscription` in the account shard
  through generated idempotent endpoints. A deterministic `user_id +
  stock_code` identifier suppresses duplicate state changes, while each actual
  change records `signal.subscription.updated` in that shard's Outbox. The
  generated relay invokes a consumer-owned topology hook before publishing; the
  KIS hook declares the projection queue. The message worker claims the event
  ID in the global automation Inbox before upserting the generated
  `SignalSubscriptionProjection` read model in that same transaction and does
  not overwrite a newer recorded revision. Each newly saved global delivery
  intent records `signal.delivery-intent.created` in the same automation Outbox;
  its account-shard Inbox consumer saves one deterministic generated
  `InAppNotification` record without an external side effect. An authenticated
  user endpoint reads the caller's newest 100 records from that same account
  shard and marks only a caller-owned record read. An isolated PostgreSQL
  verification applied the complete account `upgrade heads` graph, then saved,
  retrieved, and newest-first listed generated notification records through its
  account-shard repository; its temporary container was removed afterward.
  External delivery and orders remain outside this slice. KIS also exposes the
  enabled global projection through an operator-token-protected lookup by
  domestic stock code; its list query remains consumer-owned.

AutoForge currently has working foundations for:

- specification and generation contracts
- manifest and file ownership
- one generated FastAPI composition that wires every selected
  `application.modules` entry into the same application; selecting different
  module sets for independent generated application deployment units is not
  implemented yet
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
- authenticated Control Plane service-heartbeat intake backed by PostgreSQL:
  bounded dependency summaries, server-owned expiry, and active-report queries.
  An isolated PostgreSQL verification applied migrations `001` through `006` and
  confirmed heartbeat upsert, database-timestamped expiry, and active-report
  retrieval.
- opt-in generated FastAPI service-heartbeat reporter: the application lifespan
  starts it only after generated database/session-store lifespans; missing endpoint
  or token disables reporting without affecting readiness. The local Compose profile
  passes the empty-by-default endpoint and token environment contract into the
  application container. Generator/specification/Compose focused tests pass, and
  an in-process generated-reporter to Control Plane interoperability test confirms
  authenticated storage of normalized instance/version/dependency data.
- generated scoped service-token authentication: `ApplicationSpec.service_tokens`
  declares unique named internal callers; generated module endpoints may require
  one by name, and missing or mismatched Bearer credentials fail closed. KIS
  validates that its Durable Job and operator-search APIs reject each other's
  token while accepting their own. This internal-service boundary is separate
  from generated human session access-level authorization and order request
  replay.
- KIS profile updates now reuse the generated profile Repository and Outbox
  boundary: a sequential repeat with the same resulting profile performs no
  database save and emits no second `account.profile.updated` event. This is
  consumer-owned duplicate-event suppression, not a cross-replica request-replay
  or ordering guarantee.
- generated human session access authorization: `EndpointSpec.access_level`
  supports `user`, `operator`, `developer`, and `administrator`, requires
  `current_session`, and cannot share an endpoint with a service token. The
  generated guard reads the Redis session claim and returns `403` for a missing,
  invalid, or insufficient level. The reusable `identity_session_profile`
  Blueprint now generates global `LoginAccount.access_level` (`user` by default)
  and `AccessLevelAudit` schema/repositories. KIS validates that generated
  contract with its consumer-owned incremental migration, copies the level into
  each login session, and declares generated account-profile routes as `user`.
  Its focused HTTP test proves an operator guard denies `user` and invalid claims
  while allowing `operator`. KIS now has a user-owned local `provision_operator`
  CLI: it commits a `user` to `operator` change with one audit record, then
  revokes existing Redis sessions. A retry for an existing operator only repeats
  session revocation. It intentionally rejects administrator grants and access
  downgrades until a session-version invalidation contract exists. KIS now also
  exposes a read-only `/api/identity/operator/session` endpoint generated from
  `EndpointSpec.access_level: operator`; its preserved handler returns the
  authenticated user ID and operator level. Focused and full KIS tests verify
  the generated HTTP authorization path. A fresh disposable current Compose
  profile also verified the live flow through Nginx: the endpoint returned
  `403` before provisioning, the old session returned `401` after the CLI
  revoked it, and a new login returned `200` with `operator`. The consumer
  audit migration uses an Alembic revision ID within the default 32-character
  version column limit. The separate legacy scale-out Compose profile still
  exports `REDIS_CLUSTER_URL` while the current session provider requires
  `REDIS_URL`; it is a historical profile and is not used with the default
  standalone image. A fresh generation from `autoforge.ha.yaml` now validates
  successfully and emits the cluster provider plus matching
  `REDIS_CLUSTER_URL`/`REDIS_CLUSTER_STARTUP_NODES` Compose and Kubernetes
  Secret contracts. That generated HA workspace then passed the disposable
  Redis runtime drill: a session survived `redis-7000` primary loss and
  `redis-7004` promotion, the application stayed healthy, and the stopped node
  rejoined as a replica.
- generated FastAPI application composition now always has an outer lifespan and
  keeps `application/extensions.py` scaffolded. Consumers may add ordered
  `USER_LIFESPANS` contexts after generated database, session, and heartbeat
  contexts are ready; `AsyncExitStack` closes them first. Older preserved
  extensions without that new optional tuple remain compatible. Focused generator
  tests, the full AutoForge suite, and a disposable KIS regeneration all passed.
- generated named application compositions: `ApplicationSpec.compositions`
  now emits a selected-module ASGI entrypoint under
  `application/compositions/<name>.py`, while the default `main:app` remains the
  combined application. The entrypoint reuses the generated health, lifespan,
  and selected generated domain routers but intentionally excludes the global
  `USER_ROUTERS` scaffold. KIS validates `signal_api` as a signal-only generated
  composition. `tooling.local_environment.application_compositions` now creates
  its own local Compose API service with explicit `+01..+09` port selection,
  separate log subdirectory, and the existing default application's dependency
  gates. `tooling.kubernetes.application_composition` can also select one
  declared composition for the application Deployment, running its ASGI
  entrypoint while preserving the default environment, probes, Service, and
  replica contract. KIS validates its `signal_api` selection through generated
  Kubernetes output. Dependency-isolated runtimes remain unimplemented.
- local Control Plane heartbeat deployment profile: an independently built server
  image, private PostgreSQL volume, versioned SQL initialization, loopback-only
  `49700` HTTP binding, required local secret environment file, and process
  liveness probe. A disposable Docker Compose run verified health and authenticated
  heartbeat persistence, then removed its containers, network, and data volume.
- The local Control Plane Compose profile now gives an empty private volume one
  migration owner: the one-shot `control-plane-migrate` service waits for
  PostgreSQL, invokes the provider CLI, and records versions before the
  long-running application may start. It no longer mounts SQL into
  `docker-entrypoint-initdb.d`. A disposable Compose run verified migration
  exit `0`, durable ledger versions `1` through `7`, and Control Plane `/health`
  `200`, then removed its containers, network, and data volume. Existing volumes
  created by the known former initialization path are reconciled in the same
  transaction: `007` seeds checksum evidence for versions `1` through `6`, then
  the executor records `7`. Isolated PostgreSQL tests covered both the current
  Docker bootstrap and that legacy no-ledger state; manually altered volumes
  still require backup and operator review.
- The core now has a provider-neutral Control Plane migration boundary:
  immutable SQL artifacts derive a checksum, ordering rejects duplicate versions,
  direct UTF-8 SQL discovery accepts the declared zero-padded filename format and
  rejects malformed or duplicate versions, applied migration evidence is
  timezone-aware, and `MigrationVersionLedger` defines the async durable-ledger
  seam. `PostgreSQLMigrationVersionLedger` and SQL `007` persist applied
  version/path/checksum evidence with database time; a disposable PostgreSQL
  drill verified idempotent re-recording and conflicting checksum rejection.
  `PostgreSQLMigrationExecutor` now applies ordered artifacts under one
  transaction-scoped advisory lock, records each success in that transaction,
  skips matching versions idempotently, rejects drift, rolls back a failed batch,
  and bootstraps the ledger when its creating artifact is supplied. Disposable
  PostgreSQL checks verified concurrent apply, rollback, and bootstrap. No
  application-startup migration, retry policy, or rollback policy exists yet.
- `autoforge migrate-control-plane` is the explicit provider CLI boundary. It
  resolves the PostgreSQL URL from an environment variable, discovers a declared
  migration directory, prints only newly applied versions, and never runs from
  application startup or generated Kubernetes resources. A disposable subprocess
  check verified first-run output and repeat-run silence for both a custom
  artifact and the actual `001`??`007` Control Plane directory.
- The Control Plane container image now packages both that CLI and the declared
  SQL artifacts while preserving its default server command. A disposable image
  check against isolated PostgreSQL applied versions `1` through `7` once and
  returned no output on the immediate repeat run.
- A disposable subprocess failure drill then supplied one valid DDL artifact and
  one invalid SQL artifact to the provider CLI. It returned nonzero with only a
  bounded error type, exposed neither the database URL nor SQL text, and left no
  ledger evidence or partially created table after transaction rollback.
- Kubernetes generation now has an opt-in Control Plane profile. It emits a
  separate `control-plane.yaml` with a two-replica Deployment, private ClusterIP
  Service, pre-created Secret references, `/health` liveness, and `/readiness`
  readiness, plus a zero-value Secret template. It does not add database or
  migration resources; provider migration remains an explicit pre-rollout
  operation. Generator and full-suite validation pass. The
  local `kubectl` client is installed; an initial client-only dry-run was blocked
  by kubeconfig/API discovery and was later superseded by the disposable cluster
  drill below.
- Docker Desktop Kubernetes runtime validation later became available. A
  disposable namespace accepted the generated Deployment and ClusterIP Service;
  after rebuilding the image, `/health` returned 200 and `/readiness` returned
  the expected 503 without a provider PostgreSQL store. The rollout correctly
  remained blocked by readiness, and the namespace was removed after the drill.
- A second disposable Docker Desktop Kubernetes drill supplied a provider-owned
  PostgreSQL endpoint initialized from SQL `001`–`006`. The generated Control
  Plane Deployment rolled out two `1/1` replicas; both returned `/health` 200,
  `/readiness` 200 with `{"status":"ready"}`, and the Service was confirmed as
  `ClusterIP:8000`. The namespace and temporary database container were removed
  after verification.
- A later disposable Docker Desktop Kubernetes migration-boundary drill ran the
  packaged provider image against isolated PostgreSQL before deploying the
  Control Plane. The migration ledger contained versions `1` through `7`; the
  runtime received its database URL only through a Secret, rolled out two current
  Ready replicas, and both returned `/readiness` 200 with `{"status":"ready"}`.
  The Service had a ClusterIP and no Kubernetes Job resource existed. The
  namespace and temporary database container were removed. This verifies the
  explicit external pre-rollout boundary, not a selected production provider,
  database HA, backup, or restore policy.
- The provider-backed Control Plane replica continuity drill deleted one running
  Pod, confirmed the surviving Pod's ClusterIP `/readiness` remained 200 and its
  local `/health` remained 200, then observed Kubernetes recreate the deleted Pod.
  Both replicas returned `Ready=True`; all disposable resources were removed.
- A subsequent disposable Kubernetes interoperability drill ran the actual
  generated KIS `service_heartbeat_lifespan` from the `kis-auto-trading:local`
  image against the Control Plane ClusterIP and provider-backed PostgreSQL store.
  After 35 seconds, the reporter's scheduled delivery produced one authenticated
  `kis_auto_trading` heartbeat record with the generated version and dependency
  summary; repeated delivery upserted that instance instead of creating a second
  active record. An earlier immediate one-shot logged a transient `URLError`, so
  the verified contract is the reporter's normal retrying lifespan rather than a
  startup-only single attempt. All disposable resources were removed.
- The Control Plane heartbeat write-continuity drill then recorded a generated
  KIS heartbeat, deleted one exact Control Plane Pod, and recorded a second
  generated heartbeat through the unchanged ClusterIP while one replica
  survived. Both authenticated records remained active within the server-owned
  TTL window, and the Deployment restored two ready replicas. This is a
  single-Pod replacement check, not database or multi-cluster failover proof;
  all disposable resources were removed.
- Control Plane HTTP health is split: public `/health` remains process liveness,
  while `/readiness` checks the configured PostgreSQL JobStore and service-heartbeat
  store through their normal read paths and returns `503` on store failure. Focused
  HTTP tests cover ready and unavailable stores. Compose intentionally continues
  to use liveness; provider migration remains an explicit pre-rollout operation.
- KIS's default user-owned specification now opts into the generated heartbeat
  reporter. Regeneration exposed and then corrected a generator-side Ruff issue
  (lifespan import ordering and an over-broad reporter exception handler). A
  separately running local Control Plane persisted one authenticated KIS report
  (`kis_auto_trading` `0.1.0`, database/session-store dependencies `ok`) while
  KIS continued to return `GET /health` through Nginx with HTTP 200. The
  endpoint and token remained in ignored local environment files.
- KIS's registered Windows Task Scheduler bootstrap was then run with the
  heartbeat endpoint/token in its existing ignored `environment/.env`. It
  rebuilt the current image and emitted a fresh second container-instance report
  to the still-running Control Plane; Nginx health remained HTTP 200.
- KIS failure-containment was verified through the same bootstrap: an invalid
  Control Plane token left KIS and Nginx health at HTTP 200, produced no newly
  accepted heartbeat, and logged only the exception type. Restoring the valid
  ignored token and rerunning bootstrap produced a new accepted report with
  database/session-store dependencies `ok`.
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
  `ElkSpec.elasticsearch_mode: cluster` additionally generates three local
  Elasticsearch members behind the same generated `elasticsearch:9200` proxy
  address. An isolated Docker drill ingested a JSON log through Filebeat,
  stopped one member, retrieved the baseline log, then appended, ingested, and
  searched a new JSON log through that stable endpoint. The drill also tolerates
  Kibana's transient connection close while the surviving search cluster settles.
  The stopped member then rejoined with three nodes, green cluster health, and no
  unassigned shards before the outage-ingested log was searched again.
  The same drill confirmed the singleton Kibana `/api/status` endpoint remained
  available. This is one-host logical storage recovery; Kibana remains a singleton.
  Multiple Kibana instances are intentionally deferred because their shared
  encryption-key and Secret lifecycle is not part of the insecure local ELK
  overlay contract.
- opt-in RAG infrastructure with Qdrant, Ollama, and one selectable search backend
  (Elasticsearch or OpenSearch), connected to generated application/worker consumers
  through an explicit external named network. `RagSpec.search_mode: cluster` now
  generates three search members behind the unchanged `RAG_SEARCH_URL` contract:
  consumers address `search:9200`, while the generated Nginx proxy retries a healthy
  member. One provider-parameterized Docker drill now verifies both Elasticsearch
  and OpenSearch: it creates a one-replica index, stops one member, writes and
  searches a new document, rereads the baseline document, then restarts the member.
  Each backend returned to three nodes with green index health and no unassigned
  shards before the outage-written document was searched again. This is one-host
  logical-node recovery.
  `RagSpec.qdrant_mode: cluster` now generates three Qdrant peers behind
  the unchanged `QDRANT_URL` HTTP contract plus a stable generated gRPC endpoint.
  An isolated Docker drill created an HA test collection with
  `replication_factor: 3` and `write_consistency_factor: 2`, wrote one point,
  stopped a peer, then wrote and retrieved a new point and reread the baseline
  point through the proxy. The stopped peer then rejoined; all three peers and
  all nine collection replicas reported active before the outage-written point
  was read again.
  Collection/shard/replica choices remain domain-owned; a Qdrant cluster does not
  automatically replicate a collection. `RagSpec.ollama_mode: replicated` now
  generates three independently volumed Ollama members behind unchanged
  `OLLAMA_BASE_URL`. An isolated Docker drill stopped one member and confirmed the
  stable `/api/tags` readiness response continued. No model is downloaded or shared
  automatically; actual inference failover requires an operator to prepare the
  selected model in every member volume. Both local standalone search paths are
  runtime-verified.
  The KIS OpenSearch profile responds on `49460`, persists its named-volume data
  across container restart, and exposes the generated hybrid-search client path.
  With the installed `embeddinggemma` model, KIS indexed and retrieved a live
  news probe through combined keyword and vector search. KIS now has a second,
  operator-owned Durable Job history consumer: it indexes `job_id`, job type,
  run key, status, bounded error/result summaries, and timestamps in a separate
  index while excluding payload values. The two consumers share only the
  KIS-local hybrid backend transport; their document projections remain
  consumer-owned. Both the default and explicit HA KIS input specifications
  declare the history-index Durable Job; a disposable HA generation verified the
  generated contract contains it. A disposable HA runtime then verified the
  generated internal API → Outbox → RabbitMQ → Durable Worker → Ollama/OpenSearch
  path with three application replicas behind Nginx. A live hybrid query returned
  the safe history projection without `payload` or internal `embedding` fields.
  The user-owned `/internal/operator/search/durable-jobs` endpoint reuses the
  generated Durable Job token dependency through the scaffolded extension-router
  hook; the same HA Nginx boundary returned 401 without a token and 200 with one.
  The parallel user-owned `/internal/operator/search/news` endpoint reuses the
  same boundary and KIS-local news consumer; its HA Nginx verification returned
  401 without a token and 200 with one canonical news result, with no internal
  `embedding` field in the response.
  A direct comparison of the two operator consumers confirms that only their
  transport, token boundary, query bounds, and unavailable-backend handling are
  shared. Their source identities, document projections, field exclusions, and
  relevance fields differ, so the roadmap prerequisite for a generic
  record-to-search generator is not yet met and no generic route was added.
  The existing terminal-retry event records are deliberately not exposed through
  that operator router: current Elasticsearch access is a generated local
  Filebeat development collector, not an application query contract. It has no
  application-owned authenticated endpoint, retention policy, or approved
  redacted response projection, so adding a direct log-search client would
  prematurely expose arbitrary log fields.
  The canonical observability contract already selects provider-side log
  exploration: generated applications do not query Elasticsearch or Kibana.
  Local operators use the generated observability profile, while any production
  query API remains a deployment-provider concern rather than a KIS route.
- default-generated, profile-selected MinIO S3-compatible local storage with
  idempotent backup-bucket bootstrap; generated Compose and an actual MinIO
  backup round trip are runtime-verified
- `StorageSpec.mode: distributed` now generates four MinIO members behind the
  same `minio:9000` application endpoint, with generated API/console proxies.
  A disposable Docker drill wrote and read a baseline object, stopped one MinIO
  member, then wrote and read a new object and reread the baseline object through
  that stable endpoint. The stopped member was restarted, all four members
  reported `online`, and the outage-written object remained readable. This is
  one-host logical-node recovery evidence, not physical-host HA.
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
- The generated KIS single-host profile is runtime-verified through Nginx:
  Global identity signup/login, Redis-backed session validation, sharded account
  profile persistence, and transactional Outbox publication to RabbitMQ followed
  by idempotent inbox consumption. A Patroni leader stop preserved new
  signup/login through the HAProxy writer, and a Redis primary stop preserved an
  existing session plus a new login before the stopped node rejoined.
- RabbitMQ-enabled local profiles now generate the Outbox relay and the
  scaffolded application message worker independently of Durable Jobs. RabbitMQ
  readiness waits for its AMQP listener, preventing a false-ready startup race
  for those consumers.
- Generated single-host bootstrap rebuilds the application image before Compose
  startup, so regenerated messaging contracts cannot be hidden by a stale local
  image. KIS's three-node RabbitMQ cluster now has persisted broker state behind
  HAProxy; both profile event and dead-letter queues were verified as quorum
  queues, and a new profile event was published and consumed after one broker
  stopped and rejoined.
- The same KIS cluster proof now covers Durable Jobs: an external-call-free
  `news_index` job completed through API, Outbox, the quorum durable-job queue,
  and the generated worker both normally and while `rabbitmq-0` was stopped.
  The broker then rejoined all three running cluster nodes.
- With the separately managed generated RAG overlay started, KIS completed a
  live `news_collection` job and its generated `news_index` handoff through
  the RabbitMQ cluster. The selected OpenSearch index increased from 20 to 29
  documents. A prior failed index Job correctly exposed that the RAG overlay
  was not running; it was an operator-state failure, not a broker failure.
- RAG-enabled generated Durable Workers now report ready only after RabbitMQ,
  the selected search backend, and Ollama respond. KIS regenerated this
  contract and verified the worker healthy with its separately managed RAG
  overlay running.
- KIS stopped only the RAG Ollama service for the healthcheck threshold: the
  Durable Worker became `unhealthy`, then returned `healthy` after Ollama
  recovery. RabbitMQ and database services remained untouched.
- RAG-enabled single-host README generation now documents the separate RAG
  overlay and inference-profile startup order; the generated KIS README was
  regenerated and pushed without merging Compose projects.
- The generated Windows single-host bootstrap now checks the resolved external
  RAG network before image build or Compose startup. When RAG is selected, it
  then performs read-only in-network requests to the configured search and Ollama
  endpoints after image build and before application startup, passing Python source
  through standard input to avoid Windows native-argument quoting; the durable-worker
  healthcheck remains the final readiness authority. A live KIS HA RAG drill passed
  that preflight and then created the HA services; stopping Ollama produced the
  explicit preflight error before application startup and recovery restored it. The
  full HA startup then encountered stale local Patroni DCS state from prior retained
  volumes, so the lightweight default profile was restored without deleting data.
  A separate fresh-volume HA RAG drill then used the isolated
  `autoforge_ha_rag_drill` Compose project and the non-overlapping `51400` port
  block: the RAG overlay, three application replicas, Nginx, PostgreSQL HA,
  Redis Cluster, RabbitMQ HA, and Airflow reached their declared ready or healthy
  states, and both Nginx and Airflow health endpoints returned HTTP 200. Manually
  stopping one application replica left Nginx health at HTTP 200 and the replica
  returned healthy after it was started again. A later generated profile-server
  drill terminated application PID 1 from inside the container after Docker's
  restart-policy activation window: six consecutive Nginx `/health` requests
  remained 200, and the same application container returned `healthy` with
  `RestartCount: 1`. This proves one-host process recovery and replica continuity,
  not physical-host HA.
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
- The opt-in `airflow_scheduler_replicas: 2` profile is runtime-verified from the
  current KIS HA specification in an isolated generated environment using
  PostgreSQL HA. Both schedulers became healthy; after stopping one, the
  survivor kept the triggered `durable_job_news_collection` run in `running`
  state. This verifies scheduler continuity and DAG handoff; the downstream
  business handler remains fixture-owned and is not part of this infrastructure
  proof. See
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

- KIS news now normalizes provider text as `summary`, then `description`, then
  `title`; AutoForge generates the nullable canonical persistence field while a
  consumer-owned incremental migration protects existing production rows. The
  focused normalization, hybrid-indexing, durable-job, and migration-graph
  tests pass. An isolated runtime drill applied the baseline and incremental
  migrations, collected and indexed ten AAPL articles, and confirmed a
  non-empty `content` field with OpenSearch `text` mapping.

- Optional generated artifacts now retain manifest ownership when a profile is
  disabled. A disposable KIS lifecycle proved enable → disable → changed-port
  re-enable for RAG, and the tracked KIS manifest safely re-adopted its matching
  historical RAG, ELK, Filebeat, PostgreSQL HA, and RabbitMQ HA outputs without
  changing their file content.

- KIS Yahoo collection already uses a 30-second provider timeout and classified
  Yahoo errors. Its consumer-owned Durable Job handler requests at most three
  exponentially delayed retries, and focused tests now cover both timeout and
  provider-level failures at that same retry boundary.

- KIS `news_index` now reuses that durable retry path for transient RAG
  dependencies: network errors and HTTP 408, 429, and 5xx requeue the same
  canonical `source_keys`; non-transient HTTP 4xx errors remain failed. The
  focused handler tests cover all of those classifications. An isolated runtime
  drill collected and initially indexed ten AAPL articles, stopped only Ollama,
  observed the original index Job fail, restored Ollama, and observed its
  `retry:1` Job succeed with ten OpenSearch documents retained.

- KIS keeps canonical Yahoo News collection available when its optional RAG
  profile is disabled: it records an explicit `indexing_status: skipped` result
  and structured skip signal instead of enqueueing an un-runnable index Job.
  A manually requested index Job follows the same explicit no-op path; configured
  RAG continues to use the existing index and retry contract.

- A final transient `news_index` failure now emits the structured
  `news_index_retries_exhausted` signal with the job identity and bounded retry
  metadata. The focused test proves that it does not create a fourth Job.

- The generated Durable Job API has focused KIS contract coverage for idempotent
  execution, job-type-scoped recent-history retrieval, status/result retrieval,
  requested-job cancellation, and
  cancellation races. When Control Plane heartbeats are enabled, the generated
  Durable Worker reuses that push contract under its own service identity;
  Compose passes the same opt-in endpoint and token environment to it. The
  rebuilt single-host application returned HTTP 200 for the authenticated recent
  history route; its current development database contains no job records.

- Fresh KIS profile generation confirms the local proxy boundary: the base
  integration Compose remains dependency-oriented, while the generated
  `single_host` overlay adds Nginx and the configured application scale. The
  default KIS overlay has one application replica; its HA overlay has three.
  The Windows bootstrap generator test now explicitly asserts both environment
  files and both Compose files, preventing a boot path that omits that overlay.

## Docker work

- The generated `environment/service-composition.json` now records stable
  API, relay, worker, scheduler, initializer, and infrastructure roles in
  addition to lifecycle, health, dependencies, and configuration contracts.
  KIS HA regeneration verified the role metadata without changing service
  names or runtime behavior.

- Local Environment Generator는 생성된 Compose에서 파생한
  `environment/service-composition.json`을 함께 생성한다. 이 generated-only manifest는
  서비스별 configuration environment name, lifecycle/restart policy, healthcheck,
  dependency condition과 Redis/RabbitMQ/Durable Job 계약을 기록하며, 별도 명세나
  런타임 제어면을 만들지 않는다. KIS 기본 명세를 재생성해 11개 Compose service의
  lifecycle·health 조건이 manifest와 일치함을 확인했다.

The optional Dockerfile Generator and generated-project daemon build are verified.
Local/integration Compose and Kubernetes base manifests are generated under their
own contracts. Artifact publishing, live deployment, and cloud credentials are not
owned by the Dockerfile Generator.

`DockerfileGenerator` now also renders a generated `Dockerfile` whenever the
local application runtime is enabled, even when `tooling.docker.enabled` is not
set. This closes a real empty-workspace failure in which generated Compose used
`build: Dockerfile` but depended on a stale pre-existing file. The project
validator also passes `--no-cache-dir` to `pip wheel`, avoiding a Windows shared
pip-cache ACL failure without changing generated package contents.

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
A generated profile-server drill also terminated the singleton single-host Nginx
PID 1 from inside its container after Docker's restart-policy activation window.
The same container returned `healthy` with `RestartCount: 1`, and the unchanged
public `/health` endpoint returned 200. This verifies bounded one-host proxy
process recovery; the intentionally singleton local proxy can have a brief gap.
A fresh empty workspace generated from KIS `autoforge.ha.yaml` now independently
passed the complete AutoForge generation validation, then started the same Nginx
and three application replicas with three etcd members, three Patroni PostgreSQL
members, six Redis Cluster members, and three RabbitMQ members. Restarting one
application container preserved proxied health and recovered that container. The
drill used its own `596xx` host ports, Compose project, and volumes, leaving the
running lightweight KIS profile unchanged.
The same generated workspace then passed the existing isolated PostgreSQL HA
drill: stopping `postgres-ha-0` promoted `postgres-ha-1`, HAProxy restored the
unchanged application writer contract, and the stopped member rejoined as a
replica. A full HA dependency-stack restart also restored the Redis Cluster and
application health, and an explicit Patroni candidate recovered the intentionally
leaderless three-member cluster. This is one-host logical-node failover evidence,
not physical-host or multi-host recovery proof.
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
host port. Generated applications use `/readiness` for dependency readiness and
`/health` for process liveness. A rebuilt default KIS Compose application is
healthy under that `/readiness` check; its internal `/readiness` and proxied
`/health` each returned HTTP 200. Explicit
SIGTERM/preStop draining, KIS OAuth token coordination, and multi-node log
persistence remain unverified. A Docker Desktop Kubernetes check applied the
generated profile, observed 2/2 proxy and 3/3 application readiness, returned
`GET /health` through a temporary port-forward, and recovered one replaced Pod
from each Deployment. This is a single-node validation, not multi-node HA proof.
The Kubernetes Nginx template forwards `X-Real-IP`, `X-Forwarded-For`, and
`X-Forwarded-Proto`.

A fresh KIS HA workspace then built its generated Dockerfile and applied its
generated Kubernetes base-server manifest in an isolated Docker Desktop
namespace. With a validation-only Secret, all three application Pods and both
Nginx Pods became Ready; an Nginx-local request traversed the internal ClusterIP
backend and returned `/health` 200. Deleting one application Pod restored three
current Ready Pods while that route remained healthy. The namespace was removed.
This proves generated local Kubernetes topology and Pod replacement only, not
provider database, Redis, RabbitMQ, or multi-node Kubernetes failover.

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

The PostgreSQL/Redis drill now rejects a default single-host workspace and
accepts only an isolated output generated from KIS `autoforge.ha.yaml`; its
test-only KIS, Airflow, and host-port values keep that output independent of the
running default profile. A fresh generated workspace passed the complete
Patroni leader-stop/promotion/rejoin, intentional leaderless recovery, Redis
network restart, and Redis primary-promotion checks. Its companion
`kis-auto-trading/scripts/verify_generated_rabbitmq_ha.py` starts the generated
three-node broker cluster only, verifies a quorum queue through HAProxy, repeats
the publish/consume operation with one broker stopped, and verifies that broker
rejoins. These are reproducible single-host Docker recovery proofs, not
multi-host failover, replay, or in-flight application-delivery guarantees.
The independent generated Airflow scheduler drill also completed: the scheduler
registered its generated DAG, ran an isolated historical execution, and handled
the cancelled Durable Job path without invoking a business provider.

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
application dependency readiness healthcheck healthy across a PostgreSQL restart;
the `/readiness` endpoint probes internal PostgreSQL and Redis reachability. Redis Cluster mode
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
After the RabbitMQ quorum-cluster regeneration, the same bootstrap rebuilt the
current application image and restored the complete declared profile: three API
replicas, Nginx, both RabbitMQ consumers, PostgreSQL HA, Redis Cluster, and
Airflow all reached their declared healthy or completed state.

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
selected future Kubernetes MySQL HA provider is MySQL Operator for Kubernetes;
its opt-in specification contract and generated `InnoDBCluster` manifest are
implemented. Its generated bootstrap Secret template and README describe the
separate root-account and TLS Secret prerequisites, but no Kubernetes runtime
verification has run yet. Read-only preflight found one ready Docker Desktop
Kubernetes node but no MySQL Operator CRD, so runtime validation remains an
external installation prerequisite. The
generated application starts and retains its
`/health` contract throughout that failover verification. PostgreSQL-specific
messaging/Durable Jobs remain excluded from the MySQL profile. The published
`mysql/mysql-router:8.0` image remains incompatible with MySQL 8.4 writer
routing and is not generated.

A fresh, isolated KIS HA workspace generated from the current AutoForge source
was then verified for Redis primary failover without changing any generated
Compose artifact. The generated `RedisSessionStore` wrote and read a valid
session, its elected primary `redis-7000` was stopped, `redis-7004` promoted
while all 16,384 slots remained available, and the same session was read through
the generated multi-startup-node client contract. The Nginx health endpoint
remained available; restarting `redis-7000` returned it as a healthy replica.
This is single-host container resilience, not host or availability-zone HA.

The same procedure is now a KIS user-owned operational verifier at
`scripts/verify_generated_redis_failover.py`. It reuses the existing isolated
Compose lifecycle, requires an explicit HA generated workspace, and rejects the
lightweight standalone-Redis profile before Docker startup. The verifier passed
against the current generated KIS HA workspace: `redis-7000` stopped,
`redis-7004` promoted, the generated multi-startup-node session client retained
the session, application health remained available, and `redis-7000` rejoined as
a replica.

A disposable KIS scaffold-preservation drill then generated the current HA
workspace, placed the existing consumer-owned identity handler and its direct
password helper into it, and regenerated. Both extension file hashes were
unchanged; the manifest recorded `handlers.py` as `scaffolded` and `preserved`.
This confirms the intended boundary: AutoForge owns generated infrastructure,
routes, and models, while KIS owns its login and password policy.

The preserved extension then passed a complete disposable HA vertical drill.
The generated image built from that workspace and its generated routes completed
signup, login, Redis-backed session validation, and shard identifier retrieval
through HTTP; `/health` remained `200`. The temporary Compose project and its
volumes were removed afterward. This proves the generated skeleton and the KIS
consumer extension compose correctly; it is not a claim that domain handlers are
generated automatically.

`tooling.search` now generates an opt-in `infrastructure/search` runtime
contract for Elasticsearch or OpenSearch: configuration, async HTTP client,
protocol, deterministic fake, health check, document index/delete, raw query,
and explicit async close boundary. The generated project receives the runtime
`httpx` dependency only when selected. Index mappings, embeddings, document
projection, relevance, FastAPI lifespan registration, and KIS adoption remain
consumer-owned. AutoForge generator, Spec, and plugin regression tests passed
(`283 passed`); no external search container or KIS runtime was started for this
generator-only slice.

`tooling.vector_store` now generates an opt-in `infrastructure/vector_store`
runtime contract for Qdrant: configuration with optional API-key environment
reference, async HTTP client, protocol, deterministic fake, readiness check,
point upsert/delete/get, raw query, and explicit async close boundary. Qdrant
collection schema, vector dimension, distance metric, embedding, hybrid
relevance, FastAPI lifespan registration, and KIS adoption remain consumer-owned.
No Qdrant container was started for this generator-only slice.

The existing `StorageSpec` and `ObjectStorageGenerator` now support the separate
`runtime_enabled` selection. It generates `infrastructure/object_storage` with
S3-compatible configuration, deterministic fake, aioboto3 lifecycle adapter,
and byte put/get/delete/list operations while retaining the existing MinIO
overlay. The generated adapter passed a disposable MinIO verification for bucket
readiness and put/get/list/delete; its container and temporary workspace were
removed afterward. Object layout, retention, encryption, presigned URLs, FastAPI
lifespan registration, and KIS adoption remain consumer-owned.

`tooling.external_provider` now generates an opt-in
`infrastructure/external_provider` runtime contract with URL configuration,
health check, response bytes/status/headers, deterministic fake, async HTTP
adapter, and explicit close boundary. Bounded transport retry is safe-method
only by default (`GET`, `HEAD`, `OPTIONS`); a caller must explicitly opt in to a
retry for a side-effecting request. Provider credentials, token coordination,
domain payloads, idempotency policy, FastAPI lifespan registration, and KIS
adoption remain consumer-owned. Generator plan, generated fake, and HTTP retry
classification are verified through a deterministic `httpx.MockTransport`; no
external provider or KIS endpoint was called for this slice.

`tooling.distributed_lock` now generates an opt-in
`infrastructure/distributed_lock` runtime contract for standalone Redis, Redis
Sentinel, or Redis Cluster selection. It uses a TTL lease acquired with `SET NX
EX` and an owner-token Lua release, with a deterministic fake covering expiry
and stale-owner rejection. The generated standalone adapter passed a disposable
Redis verification for acquire contention, wrong-owner rejection, and correct
owner release; the temporary container and workspace were removed afterward.
An isolated generated six-node Redis Cluster drill then acquired and released a
lock through the multi-startup-node adapter, stopped one primary, waited for
cluster recovery, and repeated the same lock operation. The shared local
environment now generates Sentinel primary/replica/quorum topology. This is not
a Redlock, fencing-token, or auto-renewal
implementation. Lock key design, critical-section duration, wait/retry policy,
token-cache policy, FastAPI lifespan registration, and KIS adoption remain
consumer-owned.

`tooling.key_value_store` now generates an opt-in
`infrastructure/key_value_store` runtime contract for Redis or Memcached
selection. Redis supports standalone, Sentinel, or Cluster selection; Memcached
uses one configured endpoint and rejects Redis topology modes. Both adapters
provide TTL `get`/`set`/`delete`, a deterministic expiry fake, health check, and
explicit async lifecycle without adding a global cache singleton or application
cache policy. The selected adapter and dependency are generated from the
specification. The generated Redis standalone adapter passed a disposable Redis
verification for set/get/delete; the Memcached adapter is deterministically
verified through its provider client contract and an opt-in generated Memcached
Compose runtime drill. Memcached is internal-only on the Compose network. When a
local profile selects Redis Session, DistributedLock, or Redis KeyValueStore,
their Redis modes must agree and their selected connection environments are
injected into application and Durable Job worker containers. An isolated
generated six-node Redis Cluster drill set, read, and deleted a value through
the multi-startup-node adapter, stopped one primary, waited for cluster recovery,
and repeated the same operation. A generated local Sentinel drill formed a
three-Sentinel quorum, stopped the primary, observed a new master, then repeated
the generated key-value set/read/delete contract. Value serialization, cache
invalidation, key design, FastAPI lifespan registration, and KIS adoption remain
consumer-owned.

The opt-in Memcached Docker drill now exercises the generated adapter against the
real internal `memcached:11211` endpoint before and after terminating container
PID 1. It waits for Docker's ten-second restart-policy activation window, verifies
`RestartCount` increases and health returns, then sets and reads a fresh key.
Pre-restart cache loss remains valid cache-miss behavior; this is process recovery,
not Memcached replication, durability, or HA.

The same generated `DistributedLock` Sentinel client acquired and released a
lock before the primary stopped, remained alive through quorum failover, then
acquired and released that lock again after the new master was stable. A transient
master-discovery failure during the switch remains observable to callers; AutoForge
does not silently retry a lock command whose execution result could be uncertain.

The generated FastAPI `session_store_lifespan` also kept its same
`RedisSessionStore` client through the local Sentinel failover drill: it created
a session before the primary stopped and read the same session from the new
primary after the Sentinel view was stable. This verifies local failover recovery,
not a zero-RPO guarantee for Redis's asynchronous replication.

The generated `request_replay_store` was separately verified in that Sentinel
topology. The drill used `WAIT(2, 10_000)` only as a test precondition to confirm
both replicas had acknowledged a pending replay claim, stopped the primary, then
used a fresh generated lifespan/provider connection to complete and re-read that
same record from the elected master. This proves the explicit replicated-record
and reconnect boundary; it does not make `WAIT` a generated default or promise
zero RPO or transparent recovery for an in-flight HTTP request.

The same bounded drill now renders a real `EndpointSpec.idempotency` POST route.
It completes the first request before failover, confirms the completed record was
acknowledged by both replicas, then starts a fresh generated application lifespan
after promotion and receives the original JSON response without invoking the
replacement handler. The two HTTP checks share the existing pre/post-failover
probe containers so local test load does not distort Sentinel election timing.
The promoted-master check also reuses that idempotency key with a changed request
body and receives the generated 409 conflict before the replacement handler can
run. A separate post-failover key then forces the fixture handler to return 500;
the generated exception path aborts that pending claim, and a caller-initiated
retry with the same key and body succeeds once the fixture handler is replaced.
This verifies claim cleanup, not automatic request retry. A concurrent
post-failover pair with the same key and body also leaves the first handler held
behind an async event, returns the generated 409 in-progress response to the
second request, and completes the first request with exactly one handler call.

`tooling.realtime` generates an opt-in `infrastructure/realtime` runtime
contract with an asynchronous in-process `RealtimeHub`, channel
subscribe/unsubscribe/publish, explicit close, and a deterministic subscriber
fake. Its explicit `backplane: redis_pubsub` option requires the existing
single `redis_session` service and adds a best-effort
`RedisPubSubRealtimeBackplane` plus deterministic fake. Standalone, Cluster
startup-node, and Sentinel modes are generated. An isolated generated Sentinel
drill formed a three-Sentinel quorum, stopped the primary, observed the new
master, then confirmed that the existing listener reconnected and received a
newly published hint. Redis Pub/Sub remains at-most-once, so a hint published
during the transition is not a durable delivery guarantee. A disposable six-node
Redis Cluster verification confirmed global Pub/Sub delivery through ordinary
Redis seed connections before and after primary failover. KIS now selects the
contract in both standalone and HA specifications;
its default generated output and an isolated HA generated workspace both passed
validation and import checks. KIS now owns the route, authentication,
user-channel policy, and notification publisher: its application lifespan owns
the generated backplane listener; a Bearer-session USER WebSocket subscribes
only to `notification:{user_id}`; and the account-shard message worker sends a
minimal `notification_id` hint only after the durable transaction exits. A
backplane failure is logged without requeueing or changing the durable
notification; the existing notification read API is recovery. The local Compose
message worker now receives the selected Redis runtime environment and readiness
dependency when this backplane is selected, rather than requiring a hand edit.
Focused KIS worker, lifespan, WebSocket, and generated Compose checks pass.
An actual non-production Windows Compose drill also verified the complete path:
the generated migrate service applied the account notification schema, a RabbitMQ
delivery-intent event was committed by the worker, the Nginx-routed authenticated
WebSocket received its minimal `notification_id` hint through Redis Pub/Sub, and
the same caller retrieved the durable record from `GET /api/notifications`.
That drill exposed and fixed an AutoForge Alembic generator defect: when a
generated revision exceeds PostgreSQL's default 32-character version column, the
generator now emits a deterministic compact ID while retaining existing short
IDs. Existing migration files are scaffolded by design, so an unapplied affected
consumer migration was deliberately aligned with the new generated ID rather
than overwritten by regeneration.
KIS now provides the user-owned optional
`scripts/verify_realtime_notification.py` command to repeat that local proof
against an already-running non-production Compose project. It creates and
revokes an ephemeral USER session, emits one local delivery-intent event through
the existing worker, then requires the WebSocket hint and matching durable REST
record, marks that exact record read, and confirms its persisted `read_at` state.
It neither starts Compose nor calls KIS or an external delivery provider.
The existing disposable `verify_generated_single_host.py` profile now reuses
that command with three explicitly scaled, healthy application replicas and a
running message worker. It verified the same Nginx-routed realtime/durable/read
path, restarted one application container, and confirmed proxy recovery before
its normal volume and network cleanup. The same profile now also restarts the
message worker, waits for its health, and proves a second new notification reaches
the durable/read/WebSocket path before the application restart check.
The profile now writes its test events through the existing automation-store
Transactional Outbox rather than publishing directly to RabbitMQ. It restarts
the outbox relay and then the message worker, proving a separate durable
notification after each recovery through the same Nginx-routed client path.
It also restarts the volume-backed single PostgreSQL service, waits for all
application replicas to become ready, and proves a new Outbox notification
through the same path. This is a single-database restart recovery check, not
PostgreSQL HA or failover evidence.
The same isolated profile restarts standalone Redis, then proves a newly created
session plus a new Outbox notification through the Redis Pub/Sub hint path. This
is reconnect evidence for the default local profile, not Redis HA or failover.
It now also restarts the standalone RabbitMQ broker, waits for the generated
Outbox relay and message worker to become healthy again, then proves a new
Outbox notification through the same Nginx-routed durable/read/WebSocket path.
Its disposable host ports are allocated per run so this drill does not collide
with an already-running local profile. This is reconnection evidence for the
default single-broker profile, not RabbitMQ cluster HA or delivery replay proof.
No acknowledgement, replay, rate limit, or delivery observability is generated.
This is not an EventBus replacement and does not make a live hint the
notification source of truth.

The dated Base Server capability-map reconciliation found no remaining generic
service to create merely to mirror a legacy folder. Its old `websocket`,
`notification`, `email`, and `sms` entries are now covered by the generated
`realtime`, `notification`, `email`, and `sms` contracts. Its `data` and `chat`
entries remain consumer-owned product models, not reusable infrastructure
generators. The snapshot stays reference-only; this status document remains the
current implementation source of truth.

`tooling.notification` now generates an opt-in
`infrastructure/notification` runtime contract with an asynchronous generic
Webhook `NotificationDispatcher`, required URL environment contract, timeout,
explicit close, non-2xx delivery failure, and deterministic fake. It performs
one POST without automatic retry, because delivery is side-effecting. Email,
SMS, mobile push, templates, credentials, recipient/channel policy,
persistence, outbox routing, deduplication, rate limiting, broker dispatch,
and delivery observability remain consumer-owned. A consumer can compose it
with the existing generated RabbitMQ/Outbox contract instead of coupling those
responsibilities inside the notifier.

`tooling.email` now generates an opt-in `infrastructure/email` runtime contract
with SMTP configuration, explicit STARTTLS selection, paired optional SMTP
credentials, async standard-library delivery, and a deterministic fake. It can
target local SMTP or AWS SES SMTP without a provider SDK. Templates, recipient
policy, bulk delivery, retries, deduplication, outbox routing, and delivery
observability remain consumer-owned.

`tooling.llm` now generates an opt-in `infrastructure/llm` runtime contract:
an async `LlmService`, deterministic fake, explicit OpenAI Responses adapter,
and environment-backed API key/model configuration. The selected specification
must name a model; generated calls use `store=False`. Chat composition,
streaming, tool calls, prompt and conversation persistence, RAG orchestration,
authorization, and cost policy remain consumer-owned.

`tooling.sms` now generates an opt-in `infrastructure/sms` runtime contract
with `SmsSender`, deterministic Fake, and a lazy-imported SOLAPI Python SDK
adapter. It requires API key, API secret, and a registered sender environment
contract. Only one-message submission and the provider group ID are exposed;
live credentials, recipient consent, retries, idempotency, status polling,
rate limits, and cost policy remain consumer-owned.

KIS now opts into generated `signal` and internal `notification` modules for its
first Signal delivery slice.
`SignalEvent` is placed in the global automation store and
`SignalSubscription` in the sharded account store; AutoForge generated their
models, repositories, SQL, migrations, and authenticated idempotent subscription
routes successfully. Consumer-owned handlers persist one SignalEvent without an
unroutable Outbox event, manage a deterministic per-user domestic-stock
subscription, and record each enabled-state change as
`signal.subscription.updated` through the existing Outbox. The generated relay
calls a consumer-owned topology hook before publishing; KIS declares its
projection queue there. A generated global SignalSubscriptionProjection plus
consumer-owned incremental migration and message-worker handler apply a newer
revision once through the automation Inbox. Each newly persisted global delivery
intent emits a same-transaction Outbox event whose account-shard Inbox consumer
saves one deterministic generated `InAppNotification` record. Market-data
monitoring, user-facing notification policy, external delivery through
Messaging/Realtime/Notification, and orders remain consumer-owned.

KIS now selects the generated external-provider, distributed-lock, and
key-value-store contracts in both its default standalone and HA Redis Cluster
specifications. Its user-owned `KisTokenCoordinator` composes those contracts
for the official `POST /oauth2/tokenP` client-credentials request: it caches a
validated token with a 60-second expiry safety margin, uses a per-credential
hashed Redis lock/cache scope, re-checks the cache after lock acquisition, and
does not retry the POST automatically. Focused fakes verify cache reuse, lock
release after an invalid response, refresh-in-progress handling, and the
official request shape. Regenerating KIS exposed generated Ruff defects in the
three contracts; AutoForge corrected the Enum default and import rendering at
the generator source. AutoForge regression is `613 passed, 17 skipped`; KIS is
`74 passed, 1 skipped` with one pre-existing FastAPI/Starlette `TestClient`
deprecation warning. No live KIS credential, token request, trading route, or
order was executed.

`ApplicationSpec.runtime_environments` now supplies the generic generated
runtime-environment contract that a consumer needs before it can register a
credentialed client. It stores names, local requiredness, and a non-secret
`health_test_value`; the generated health test uses that value before lifespan
startup, while Compose, Kubernetes, and environment examples receive names only.
Names remain unique and cannot collide with generated service-token or heartbeat
names. Required values fail fast in local Compose; Kubernetes still requires
every declared Secret key. The contract is verified by focused specification,
local-environment, Kubernetes-generator, and FastAPI-project-generator tests.

KIS now declares `KIS_API_URL`, `KIS_APP_KEY`, `KIS_APP_SECRET`, and optional
`KIS_TOKEN_SCOPE` through that contract in both standalone and HA
specifications. Regenerated Compose fails fast for the first three values and
Kubernetes references all four from its application Secret. The user-owned
`KisMarketDataClient` shares the generated external-provider boundary and the
token coordinator, exposing only domestic-stock current-price `GET
/uapi/domestic-stock/v1/quotations/inquire-price` with `FHKST01010100`. It
validates the six-digit stock code, checks the KIS HTTP/envelope response, and
uses fake transport tests for the request headers, query, success, and error
paths. It is registered through the generated `USER_LIFESPANS` extension hook:
startup constructs and stores it in `app.state` without a KIS request, and
shutdown closes its shared HTTP and Redis clients. It has no FastAPI route,
makes no live request during startup, and exposes no account or order operation.

KIS now also has a user-owned `KisDomesticAccountClient` for the official
read-only domestic balance `GET /uapi/domestic-stock/v1/trading/inquire-balance`.
It reuses the same generated external-provider and Redis-backed token
coordination contracts, validates application-only account runtime values,
selects the real/demo TR ID, and follows at most ten continuation pages. It
returns typed holding fields only. A user-owned application lifespan owns its
close boundary, and the internal operator-token-protected
`GET /internal/operator/portfolio/domestic-stock-holdings` route returns that
list with safe 502/503 failures. It has no persistence, account-summary
exposure, or order behavior. Fake transport and FastAPI tests cover the request
shape, pagination, provider failure, invalid account configuration, token guard,
safe projection, and safe failure mapping. No KIS balance request has run.
The configured brokerage account is deployment-scoped runtime configuration,
whereas KIS user profiles are partitioned by `user_id`; the current contracts do
not establish a mapping between them. Live KIS holdings therefore remain the
source of truth. No portfolio table, cache, or Durable Job is generated or
implemented until a stale-data policy, snapshot purpose, and explicit account
ownership mapping exist.

The consumer's two read-only KIS clients now reuse the same generated
`KeyValueStore` instance as their token coordinator for short-lived reads:
domestic current prices use a two-second cache and domestic holdings use a
fifteen-second cache. Cache keys hash credential or account identity rather
than storing it in Redis key text. This is a consumer-owned rate-limit and
latency optimization, not a generated stale-data policy, and it does not
change either client's read-only boundary. Fake-transport verification covers
the cache hit paths together with token coordination, API, lifespan, and
Durable Job handler coverage (`38 passed`). Malformed cached values fall
through to the existing read-only KIS request rather than being trusted; the
live opt-in checks remain unexecuted.

KIS also has a default-skipped integration check for that balance client. It
requires an explicit opt-in flag and the KIS application/account environment
values, makes one read-only balance request, validates only the typed holding
result, and closes its HTTP/Redis resources. It has not been run with live
credentials.

`RuntimeEnvironmentSpec.targets` now declares the generated runtime process
that receives each value, defaulting to `application`. KIS targets its four KIS
values at both `application` and `durable_job_worker`; regenerated Compose
therefore gives the durable worker the same credential references without
leaking them to unrelated roles. The generated worker subscribes to the manual
`market_price_snapshot` job. Its user-owned handler validates a six-digit stock
code before I/O, reads one price through `KisMarketDataClient`, writes one
global `automation` snapshot, and closes its per-job client. The handler and
worker tests use fakes only; no scheduled collection, live KIS request, or
order behavior exists. Kubernetes now generates an internal Durable Job worker
Deployment when Durable Jobs are declared: it has no public Service, uses the
generated worker command, receives database/service and worker-targeted Secret
bindings without service tokens, and probes RabbitMQ. Its replica count is a
separate Kubernetes setting (one by default; KIS HA selects two). The local
durable worker also receives the declared Redis standalone or Cluster environment
and readiness dependency, so the generated token cache and distributed lock use
the same topology as the application. Default and HA KIS regeneration both
verified this output; no live Kubernetes workload or KIS request was run.

The generated Durable Job trigger now calls a scaffolded, consumer-owned payload
validation hook before it opens a database session or requests an outbox record.
KIS validates only `market_price_snapshot` there, reusing its six-digit stock
code rule. Its focused internal API test proves one valid request reaches the
repository and an invalid request returns 422 without creating a job; no KIS
request runs in either case.

KIS now exposes one user-owned internal current-price route at
`/internal/operator/market-data/domestic-stock-price`. It reuses the generated
`operator` service-token guard, accepts only a six-digit stock code, obtains the
lifespan-owned client from `app.state`, and returns only stock code and current
price. Known KIS-envelope failures map to a safe `502`; token or transport
failures map to a safe `503`. Fake API tests verify authentication, safe output,
input rejection before I/O, and error-detail concealment. There is no public
route, background polling, account access, order operation, or live KIS call.

The opt-in `tests/integration/test_kis_market_data_integration.py` remains
skipped unless `KIS_READ_ONLY_INTEGRATION=1` is explicitly set. It can perform
only the existing current-price GET with configured credentials and an optional
six-digit `KIS_INTEGRATION_STOCK_CODE`, then closes its HTTP and Redis clients.
No live invocation has been authorized or executed.

KIS also provides the user-owned
`scripts/verify_kis_read_only_price.py` command for the preferred container
path. It validates the required KIS and Redis environment names without
printing their values, rejects the generated `https://example.invalid`
placeholder before I/O, then performs exactly one current-price GET through
the same application container environment. Its configuration tests pass; the
currently running local container still has the generated placeholder, so no
live invocation has run.

KIS now declares a `market_data` module through the existing AutoForge database
contract. Its `MarketPriceSnapshot` model, repository protocol/fake/SQLAlchemy
adapter, raw SQL, and independent Alembic baseline are generated from one
specification. `market_price_snapshots` is explicitly placed in the global
`automation` store because external market data is shared across users and
shards. A consumer-owned writer now creates one UUID/timestamped snapshot in
that generated repository through the existing automation session. The existing
internal GET stays read-only; a separate operator-token-protected POST requests
the price and writes the snapshot, returning a safe generated snapshot model.
Storage failures return a detail-safe 503. A separate operator-token-protected
GET reads one snapshot by UUID through the same global session and generated
`find_by_id` contract, returning 404 when absent and the same safe 503 boundary
when storage is unavailable. There is no polling job, public route, portfolio
data, order/execution behavior, or live KIS call. KIS verification is `82
passed, 2 skipped`; the one existing FastAPI/Starlette TestClient deprecation
warning remains external to this change.

An opt-in database integration test now validates the migration/runtime boundary
without a KIS request. A disposable PostgreSQL container created the four
generated logical databases, applied the full generated Alembic history
including `af_automation_market_data_0001`, then saved and read one snapshot via
the generated SQLAlchemy repository. The container was removed afterward. The
default KIS suite is `77 passed, 2 skipped`; both integration tests require
explicit external configuration, and the same unrelated TestClient warning
remains.

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
