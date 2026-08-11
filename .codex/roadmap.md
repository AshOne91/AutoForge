# AutoForge Roadmap

## Completed foundations

- specification and generation contracts
- FastAPI project/module/model/router generation
- Workspace and validation pipeline
- Plugin architecture
- PostgreSQL database generation
- Redis and RabbitMQ foundations
- Transactional Outbox
- EventBus and Pipeline
- durable GenerationJob worker model
- Git checkout/branch/commit/push/Pull Request automation
- Control Plane and Worker execution
- GitHub webhook ingestion
- GitHub Actions/Jenkins validation configuration

## Active

### Docker build

- [x] build-only responsibility contract
- [x] minimal Dockerfile Generator
- [x] generated-project Docker build-context verification
- [x] generated-project Docker daemon build verification

### Current vertical-slice direction

The target and phase order for base_server-class reusable Application Blueprints
are fixed in `docs/architecture/base_server_blueprint_strategy.md`.

After the Docker contract is verified, validate the generator against a real
consumer slice in `kis-auto-trading`, in this order:

1. generated FastAPI application starts and validates
2. database artifacts are deterministic and reproducible (verified for PostgreSQL DDL)
3. Global versus Shard persistence boundaries are explicit (verified for SQLAlchemy/Alembic)
4. shared Redis/session and message-service contracts are validated (verified)
5. KIS consumer vertical slice validates generated contracts (verified)
6. deployment-oriented generation is added only after daemon build verification

### Environment realization and integration validation

- [x] environment ownership, profile, and validation-order contract
- [x] KIS Durable Job and Global coordinator-store product declaration
- [x] local/integration environment profile contract for that declaration
- [x] Environment Generator and container vertical-slice validation

Verified on 2026-08-10 against the generated KIS Compose profile: PostgreSQL
created `identity`, `automation`, `account_shard_1`, and `account_shard_2`;
the three-node Redis Cluster reported `cluster_state:ok`; RabbitMQ passed its
healthcheck. Private service identity for the generated durable-job API is
also complete. Local Airflow runtime validation is complete, including DAG
registration and private service identity wiring.
The KIS Airflow container reached healthy status, registered
`durable_job_news_collection`, and reported no DAG import errors.
The generated migration and application containers also reached healthy status;
an unauthenticated durable-job request returned 401, while Airflow created and
queried a `requested` job through the internal application service. The generated
Outbox relay and durable-job worker then moved a real `news_collection` job to
`failed` through RabbitMQ. That terminal state is expected until the user-owned
business handler is implemented.

On 2026-08-11, the same local Compose application also validated the KIS
`signup -> login -> Redis session -> sharded profile update/read` HTTP path.
This is the first proven reference for extracting an Application Blueprint;
the generated infrastructure remains separate from KIS-owned credential and
business-handler policy.

Each step is a separate testable contract. The Durable Job trigger/status,
Outbox, worker lifecycle, and static Airflow DAG contracts are complete.
The KIS declaration, local/integration profile, local Airflow runtime, application
container, Outbox relay, and durable-job worker are validated. Airflow owns scheduling,
retry, timeout, and dependency orchestration,
not business processing. Do not introduce deployment, Kubernetes, Redis Cluster
topology, or cloud-specific behavior before a consumer requirement and an
owning generator contract exist.

## Later

- [ ] additional database providers such as MySQL
- [x] managed Redis Cluster connection contract (verified against KIS cluster)
- [ ] managed Redis Sentinel deployment verification (when selected by a consumer)
- [ ] WebSocket/additional service blueprints
- [x] Durable Job persistence and transactional Outbox contract
- [x] Durable Job trigger/status API contract
- [x] Durable Job worker lifecycle contract
- [x] Airflow DAG scaffold and trigger/status contract (static generation)
- [x] Durable Job private service identity contract
- [x] Airflow local runtime and private service identity validation
- [x] Airflow authenticated application trigger/status validation
- [x] Outbox relay and durable-job worker container validation
- [x] envelope-only Metrics Handler and sink contract
- [ ] external metrics backend adapter (Prometheus/OpenTelemetry, when selected)
- [ ] artifact publishing
- [ ] deployment plugins
- [ ] additional infrastructure/cloud automation
- [ ] AI specification assistance
- [ ] AI code-generation assistance
- [ ] dashboard/distributed-worker enhancements
- [ ] plugin marketplace

### Preserved long-term goals

These remain goals, not current implementation commitments:

- reusable domain/service/application templates derived from one specification
- reproducible SQL and migration artifacts for local or multi-node setup
- Global data (for example identity/login) separated from Shard data
- external Redis-backed shared state and session contracts
- queue/event-driven integration and transactional outbox completion
- Airflow-style scheduled ingestion as a replaceable orchestration adapter
- Docker/Kubernetes/cloud deployment plugins after build contracts stabilize
- generated-project validation in a second machine or multi-node environment

The `identity + session + sharded profile` Blueprint and the `scheduled
ingestion` Blueprint are now implemented. The next concrete milestone is to
run the generated scheduled-ingestion environment as an isolated Compose
project and validate its application, migration, Airflow, RabbitMQ, outbox,
and worker contracts together. Do not add specification-only metadata: each
Blueprint contract must change generated output and be validated by KIS or an
equivalent isolated generated-project environment.

Reference order is deliberate: `common-tool` supplies generation intent,
`game-server` supplies runtime composition meaning, and `base_server` supplies
Python/FastAPI patterns. Current AutoForge tests and ownership contracts remain
authoritative when references disagree.

Implement one bounded contract at a time.
Do not create empty future architecture merely to represent roadmap items.
