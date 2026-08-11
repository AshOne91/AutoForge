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
- [ ] KIS news vertical slice: canonical news record → durable indexing handoff → native Elasticsearch hybrid retrieval (BM25 + vector + RRF); Qdrant is an optional independently scalable vector-service expansion, not a first-slice requirement
- [ ] embedding and reranking provider contracts after the selected consumer establishes an evaluation dataset and relevance target
- [ ] Redis distributed lock after a real concurrency-critical consumer path exists
- [ ] Realtime/WebSocket and notification Blueprint after a consumer path exists
- [ ] cloud S3/object-storage provider after raw-document persistence is selected
- [ ] external-provider resiliency adapter after a provider is selected

- [ ] additional database providers such as MySQL
- [ ] managed Redis Sentinel deployment verification (when selected by a consumer)
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
