# Next Task

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
