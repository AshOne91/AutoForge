# Next Task

## Completed: Scheduled Ingestion Blueprint runtime contract

The generated `scheduled_ingestion` Blueprint has been verified in an isolated
Docker Compose project.

- PostgreSQL and RabbitMQ became healthy.
- Migration completed before the application started.
- FastAPI `/health` returned successfully.
- Airflow became healthy and registered `durable_job_scheduled_ingestion`.
- The private job API returned `401` without a Bearer token.
- An authenticated `scheduled_ingestion` request created a JobRecord and
  transactional Outbox event.
- RabbitMQ, outbox relay, and the durable-job worker moved the job to `failed`.
  This is expected because the scaffolded business handler intentionally raises
  `NotImplementedError`.

The temporary Compose project was removed after verification.

## Next product decision: KIS news ingestion business handler

The next executable work is in `kis-auto-trading`, not AutoForge.

OWNERSHIP: scaffolded / user-owned

EVIDENCE: `kis-auto-trading/.autoforge/manifest.json` marks
`src/kis_auto_trading/application/durable_job_handler.py` as `scaffolded` and
`preserved`.

The handler must not be implemented until KIS selects:

1. external news provider and access method;
2. canonical news record schema and idempotency identity;
3. persistence boundaries (PostgreSQL, S3, OpenSearch, or a combination);
4. RAG indexing handoff and failure/retry policy; and
5. credential storage and runtime identity.

Do not add a Realtime/WebSocket Blueprint yet. KIS currently has no WebSocket
consumer implementation; the only notification mention is a later Airflow plan,
not an executable product contract.

## AutoForge constraint

Do not change AutoForge-generated durable-job infrastructure to fill in KIS
business logic. A future AutoForge change is justified only when KIS reveals a
reusable generator-owned defect or selects a concrete reusable configuration
artifact contract.

## Completed: RAG infrastructure profile

The user has selected the wider goal of reimplementing all Base Server service
responsibilities as AutoForge-generated common capabilities. The inventory and
sequencing live in `docs/architecture/base_server_service_capability_map.md`.

An opt-in RAG infrastructure profile now changes generated Compose output only
when selected:

1. Qdrant for vector retrieval (`rag` Compose profile);
2. Elasticsearch for keyword/full-text retrieval (`rag` Compose profile); and
3. Ollama for local inference (`inference` Compose profile), without automatic
   model download.

It is generated-owned by `autoforge.generator.rag_infrastructure`. Focused
generator/plugin/specification tests passed, and an isolated generated
`scheduled_ingestion` project produced the generated RAG files, passed wheel
build validation, and passed `docker compose config --quiet`. No image was
pulled and no container was started.

The adjacent `storage` responsibility is also complete as
`autoforge.generator.storage`: an opt-in MinIO S3-compatible local profile with
a separate named volume, local-only host binding, and no automatic bucket
creation. The scheduled-ingestion Blueprint selects both profiles.

## Next product decision: ingestion and retrieval handoff

The follow-up consumer decision remains necessary before building ingestion or
retrieval business logic: canonical record identity, storage target, selected
external provider, credential policy, index/collection schema, and embedding
model policy. Those are user-owned KIS product decisions, not defaults for the
AutoForge generator.
