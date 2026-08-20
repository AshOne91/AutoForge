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

The execution unit is a `base_server/service/<name>` responsibility, not only
its Docker container. Each selected service must reach a reusable AutoForge
contract: specification selection, generated config/protocol/client/service
lifecycle, health boundary, fake or deterministic test seam, ownership metadata,
and one KIS consumer proof. Start from service dependencies and preserve the
current async dependency-injection style rather than copying Base Server's
process-global singleton pattern.

- [x] local integration service-composition contract: generated Compose에서 파생한
  `environment/service-composition.json`이 서비스별 configuration, lifecycle,
  health, dependency 및 Redis/RabbitMQ/Durable Job 경계를 기록한다. 향후 배포
  provider는 이 파생 산출물을 새 정본으로 바꾸지 않고 필요할 때 소비한다.
- [~] reusable-domain application composition: every domain module must remain
  reusable outside its first consumer. An application is a composition root
  that selects domain modules, shared services, lifecycle, persistence, and
  transport contracts. The same reusable modules must support one combined
  FastAPI application for a small deployment or selected independent
  application/worker deployment units for scale, fault isolation, or distinct
  runtime responsibilities. This follows the Base Server reference's separate
  Web Server and Model Server deployment units without copying its global
  ServiceContainer pattern.
  `ApplicationSpec.compositions` now proves a default combined FastAPI app and a
  named generated selected-module ASGI entrypoint from one project.
  `tooling.local_environment.application_compositions` can run that entrypoint
  as one additional generated Compose API service with an explicit local port.
  `tooling.kubernetes.application_composition` can select that entrypoint for
  the generated application Deployment while preserving its shared runtime
  contract. The remaining boundary is, only when a real consumer needs it,
  dependency isolation. Do not use Git branches as a
  deployment-topology model, create a name-only application-role abstraction,
  or couple module placement to replica count.
- [ ] KIS trading Blueprint validation: 시장 데이터 수집, KIS 인증·공유 token
  조정, portfolio, order/execution, risk limit와 감사 이력을 하나의 소비자 수직
  흐름으로 검증한다. 거래 전략과 투자 판단은 KIS 소비자 소유이며 AutoForge는
  검증된 공통 인프라·생성 계약만 일반화한다.
- [~] domain request-execution policy: `ApplicationSpec.service_tokens`와
  `EndpointSpec.service_token`은 named internal service caller를 fail-closed
  FastAPI dependency로 연결한다. 아직 endpoint마다
  anonymous, authenticated user, privileged operator, internal service 같은 호출
  정책을 명시한다. 생성기는 Redis session의 사용자 identity, user-owned role
  source, service secret, trusted ingress allowlist를 서로 대체하지 않는
  FastAPI dependency로 연결한다. 전역 `TemplateService`나 하드코딩된 IP 목록은
  생성하지 않는다.
- [x] request replay/idempotency contract: `SessionStore`와 별도의
  Redis-backed request claim/replay 계약이 `EndpointSpec.idempotency`로
  생성된다. session·endpoint·idempotency key 범위, 원자 claim, TTL, 완료 응답
  재전달, 충돌 재사용 거부, 실패 claim 해제를 구현했다. KIS `update_profile`이
  첫 consumer opt-in이며, 두 API 복제의 동시 요청에서 승자·재생·충돌 거부를
  검증했다. 주문 실행 적용은 남아 있다. 읽기 전용 조회나 이미 DB unique key로 보호되는 Durable Job에는
  추측으로 적용하지 않는다.
- [x] `base_server/service/search` runtime contract: `tooling.search` generates
  an Elasticsearch/OpenSearch common `SearchService` with config, protocol,
  deterministic fake, async HTTP adapter, lifecycle, and generated ownership
  metadata. Index mappings, embeddings, document projection, and relevance
  policy remain consumer-owned; the RAG overlay remains an infrastructure concern.
- [x] `base_server/service/vectordb` runtime contract: `tooling.vector_store`
  generates Qdrant readiness, point upsert/delete/get, raw query transport,
  deterministic fake, async lifecycle, and generated ownership metadata without
  bundling a provider SDK. Collection schema, vector dimensions, embedding, and
  hybrid relevance policy remain consumer-owned.
- [x] `base_server/service/storage` runtime contract: existing `StorageSpec` and
  `ObjectStorageGenerator` now optionally generate S3-compatible ObjectStorage
  config/protocol/fake/aioboto3 lifecycle alongside the MinIO overlay. Generated
  adapter verification passed against a disposable MinIO service; object layout,
  retention, encryption policy, and presigned URL policy remain consumer-owned.
- [x] `base_server/service/external` runtime contract:
  `tooling.external_provider` generates a generic async HTTP provider with
  config/protocol/fake/HTTP lifecycle, health, bounded retry classification, and
  generated ownership metadata. Only safe read methods retry by default;
  credentials, provider schemas, token policy, business idempotency, and KIS
  semantics remain consumer-owned.
- [x] `base_server/service/lock` runtime contract:
  `tooling.distributed_lock` generates a topology-selected Redis lease boundary
  with atomic acquisition, owner-token release, deterministic expiry fake, and
  explicit async lifecycle. It supports standalone, Sentinel, and Cluster
  connection selection without exposing topology through its interface. Redlock,
  fencing tokens, automatic renewal, critical-section policy, and KIS token
  policy remain deliberately outside the generated contract.
- [x] `base_server/service/cache` runtime contract:
  `tooling.key_value_store` selects Redis or Memcached behind one string
  key-value boundary with TTL, deterministic expiry fake, and explicit async
  lifecycle. Redis supports standalone, Sentinel, and Cluster topology; Memcached
  currently selects one endpoint. Value schema, cache-aside/invalidation policy,
  ranking, hashes, cache metrics, and KIS token-record policy remain
  consumer-owned.
- [x] local Memcached KeyValueStore profile: a selected
  `tooling.key_value_store.backend: memcached` generates an internal-only
  Compose service, healthcheck, application/worker environment contract, and
  opt-in Docker runtime drill. KIS remains on its existing Redis contract until
  a consumer deliberately changes its specification.
- [~] record-to-search boundary established by two KIS projections:
  `source_key`/`news_index` and `job_id`/`durable_job_history_index` carry only
  canonical identities or safe summaries, while the consumer owns document
  projection and hybrid query policy. The transport boundary is now generated;
  a generic projection generator remains deferred until an independent consumer
  project or an explicit ProjectSpec requirement demonstrates that its shape is
  stable.
- [ ] embedding and reranking provider contracts after the selected consumer establishes an evaluation dataset and relevance target
- [ ] Realtime/WebSocket hardening: preserve the current ADR-0004 boundary and
  add consumer-selected rate limiting, delivery/error observability, and a
  live multi-replica smoke drill only when a real consumer needs each policy.
  Do not turn best-effort live hints into durable notification authority or
  generate a universal user-channel policy. `tooling.notification` provides a separate
  one-POST Webhook delivery boundary; `tooling.email` provides SMTP delivery,
  and `tooling.llm` provides an OpenAI Responses API boundary. `tooling.sms`
  now provides a SOLAPI delivery boundary; push providers and notification
  policy remain future consumer decisions.
- [~] consumer-owned trading Signal slice: KIS now owns a generated persistence
  contract for SignalEvent and SignalSubscription plus a producer path that
  persists SignalEvent in the global automation store without emitting it until
  a delivery consumer exists. Authenticated users manage an idempotent,
  deterministic domestic-stock subscription in their account shard, and actual
  state changes record `signal.subscription.updated` in that shard's Outbox.
  The message worker projects it once into generated global storage through the
  automation Inbox, materializes one pending global delivery intent per enabled
  subscription, and exposes operator-only lookups of enabled projections and
  pending delivery intents by domestic stock code. The remaining delivery
  workflow requires an explicit external executor and delivery guarantees.
  The base_server reference combines market-data
  monitoring, technical/AI signal calculation, and notification enqueueing;
  AutoForge must not turn that domain workflow into a generic subscription
  transport or duplicate the existing Realtime/Messaging contracts.
- [x] operator-facing ingestion lifecycle endpoints: the generated Durable Job
  API provides idempotent execution, status/result retrieval, and requested-job
  cancellation; the separately generated Worker reports its health to the
  Control Plane heartbeat endpoint rather than tying work to request lifetime
- [ ] cloud S3/object-storage provider after raw-document persistence is selected

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
