# Current Status

## Stable foundation

AutoForge currently has working foundations for:

- specification and generation contracts
- manifest and file ownership
- isolated workspaces
- validation/build pipeline
- generator and validator plugins
- PostgreSQL-oriented database generation
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
- PostgreSQL, Redis Cluster, RabbitMQ, migration, application, Airflow, Outbox relay,
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
- opt-in MinIO S3-compatible local storage
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
- generated durable Jobs can cancel only before worker claim: cancelled messages
  remain harmless when delivered because the worker's atomic claim skips their
  handler; KIS verifies API cancellation idempotency and the worker boundary
  against local PostgreSQL, the Outbox relay, RabbitMQ, and the live worker
- KIS scale-out integration also runs the generated Airflow DAG against the
  live token-protected API; DAG discovery is verified and its wait task turns
  a cancelled Job into a controlled failure without invoking a handler
- `scripts/verify_scale_out.py` automates the Airflow cancellation assertion
  together with the PostgreSQL, RabbitMQ, Redis Cluster, and two-API checks
- The generated local environment separates `airflow-init`, `airflow-webserver`,
  and a long-running `airflow-scheduler`; KIS validates actual scheduler task
  execution in an isolated generated Compose project. It waits for scheduler
  DAG registration, unpauses the isolated DAG, triggers one historical logical
  date, confirms the Durable Job through the live API, and cancels it before
  worker claim. The generated test project uses port block `59400` and removes
  only its own containers, network, and volume. External news-provider calls
  and a production schedule remain unverified.
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
