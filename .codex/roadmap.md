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

- [ ] reusable service-composition contract: independently deployable services with explicit configuration, lifecycle, health, and Event/Queue boundaries
- [ ] canonical ingestion/indexing handoff after a consumer chooses its record contract
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

- [ ] MySQL runtime provider slice: typed database runtime selection, generated
  Compose profile, DSN/secret boundary, migrations, and focused validation
- [ ] Kubernetes or managed PostgreSQL HA deployment contract with multi-node
  placement, persistent volumes, backups, restore drills, and production
  observability after a deployment provider is selected
- [x] self-hosted single-host operating profile with Docker auto-start, durable
  volumes, log retention, backup/restore drills, health checks, and operator
  recovery for the generated service HA baseline
- [ ] later provider-selected Redis HA deployment contract: managed Cluster,
  Sentinel, or an explicitly selected alternative with topology, persistence,
  failover, secret, and recovery verification
- [ ] host bootstrap/deployment contract for Docker auto-start, AWS Launch Template
  UserData, image refresh, and secret injection after registry and host ownership
  boundaries are explicit
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
