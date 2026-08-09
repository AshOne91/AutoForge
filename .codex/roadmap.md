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

After the Docker contract is verified, validate the generator against a real
consumer slice in `kis-auto-trading`, in this order:

1. generated FastAPI application starts and validates
2. database artifacts are deterministic and reproducible (verified for PostgreSQL DDL)
3. Global versus Shard persistence boundaries are explicit (verified for SQLAlchemy/Alembic)
4. shared Redis/session and message-service contracts are validated (verified)
5. KIS consumer vertical slice validates generated contracts (verified)
6. deployment-oriented generation is added only after daemon build verification

Each step is a separate testable contract. The next consumer contract is
Durable Job plus trigger/status, Outbox, and worker lifecycle. Airflow is added
after that contract is verified; it owns scheduling, retry, timeout, and
dependency orchestration, not business processing. Do not introduce deployment,
Kubernetes, Redis Cluster topology, or cloud-specific behavior before a
consumer requirement and an owning generator contract exist.

## Later

- [ ] additional database providers such as MySQL
- [x] managed Redis Cluster connection contract (verified against KIS cluster)
- [ ] managed Redis Sentinel deployment verification (when selected by a consumer)
- [ ] WebSocket/additional service blueprints
- [~] Durable Job persistence and transactional Outbox contract
- [x] Durable Job trigger/status API contract
- [ ] Durable Job worker lifecycle contract
- [ ] Airflow DAG scaffold and trigger/status contract
- [ ] Metrics Handler
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

Reference order is deliberate: `common-tool` supplies generation intent,
`game-server` supplies runtime composition meaning, and `base_server` supplies
Python/FastAPI patterns. Current AutoForge tests and ownership contracts remain
authoritative when references disagree.

Implement one bounded contract at a time.
Do not create empty future architecture merely to represent roadmap items.
