# AutoForge Roadmap

Implemented and verified capabilities belong in `current_status.md`. This file
contains only future direction and unimplemented work.

## Later

### Base Server service capability completion

The long-term target is to reimplement every Base Server service *responsibility*
as a modern AutoForge capability, not to copy the legacy package tree into every
generated project. The dated inventory is preserved as
`docs/reference/base_server_service_capability_map.md`; this Roadmap owns future
sequencing.

- [x] local integration service-composition contract: generated Compose에서 파생한
  `environment/service-composition.json`이 서비스별 configuration, lifecycle,
  health, dependency 및 Redis/RabbitMQ/Durable Job 경계를 기록한다. 향후 배포
  provider는 이 파생 산출물을 새 정본으로 바꾸지 않고 필요할 때 소비한다.
- [ ] generic record-to-search handoff after consumer evidence establishes a
  common source identity, document projection, and query/relevance contract
- [ ] embedding and reranking provider contracts after the selected consumer establishes an evaluation dataset and relevance target
- [ ] Redis distributed lock after a real concurrency-critical consumer path exists
- [ ] Realtime/WebSocket and notification Blueprint after a consumer path exists:
  event-driven fan-out, in-app persistence, channel adapters, deduplication,
  rate limiting, and delivery/error observability
- [ ] operator-facing ingestion lifecycle endpoints after a consumer path exists:
  execute, status, health, stop, and data/result retrieval mapped to durable Jobs
  rather than request-bound work
- [ ] cloud S3/object-storage provider after raw-document persistence is selected
- [ ] external-provider resiliency adapter after a provider is selected

- [ ] MySQL Operator Kubernetes HA profile: multi-host placement, durable
  storage, backups, restore drills, and production observability. Do not use
  `mysql/mysql-router:8.0` with MySQL 8.4; local validation proved that
  combination closes the writer route.
- [ ] Kubernetes or managed PostgreSQL HA deployment contract with multi-node
  placement, persistent volumes, backups, restore drills, and production
  observability after a deployment provider is selected
- [x] self-hosted single-host operating profile with Docker auto-start, durable
  volumes, log retention, backup/restore drills, health checks, and operator
  recovery for the generated service HA baseline
- [ ] later provider-selected Redis HA deployment contract: managed Cluster,
  Sentinel, or an explicitly selected alternative with topology, persistence,
  failover, secret, and recovery verification
- [ ] Airflow multi-host deployment contract: webserver and triggerer replicas,
  remote executor selection, shared DAG/log storage, proxy/Ingress, and
  cross-host failure drills. The implemented single-host scheduler profile is
  recorded in [ADR-0001](../docs/adr/0001-local-airflow-scheduler-ha.md).
- [ ] host bootstrap/deployment contract for Docker auto-start, AWS Launch Template
  UserData, image refresh, and secret injection after registry and host ownership
  boundaries are explicit
- [ ] Kubernetes-native Control Plane provider/runtime deployment after a deployment
  provider is selected. The opt-in manifest generator, durable version ledger,
  provider-invoked migration executor, and resource contract are now present. Use
  the selected standard Secret binding and private ClusterIP Service from
  [ADR-0003](../docs/adr/0003-kubernetes-native-control-plane-provider.md), while
  keeping Pull probes authoritative and external synthetic probes on the consumer
  public path
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
- reproducible SQL and migration artifacts for additional database providers
- external Redis-backed shared state and session contracts
- Docker/Kubernetes/cloud deployment plugins after build contracts stabilize
- generated-project validation in a second machine or multi-node environment

Reference order is deliberate: `common-tool` supplies generation intent,
`game-server` supplies runtime composition meaning, and `base_server` supplies
Python/FastAPI patterns. Current AutoForge tests and ownership contracts remain
authoritative when references disagree.

Implement one bounded contract at a time.
Do not create empty future architecture merely to represent roadmap items.

## Capability proof target

The project is intended to demonstrate platform-level engineering, not promise a
particular salary. A credible senior/platform portfolio requires repeatable proof
that one specification can produce a runnable service, its persistence and
observability boundaries, a deployment profile, and a failure-recovery test. The
near-term proof target is the single-host operating profile; multi-host and cloud
deployment are later evidence, not prerequisites for this baseline.
