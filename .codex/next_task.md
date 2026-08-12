# Next Task

## Next executable unit: scheduler/trigger contract

The KIS terminal retry alert decision is complete for this slice: the
structured Elasticsearch event is the operator-facing baseline. External
webhook/email/SMS delivery is intentionally deferred until a destination,
payload boundary, and delivery guarantee are selected.

The next executable work is in AutoForge.

OWNERSHIP: AutoForge architecture and generation contract

EVIDENCE: `base_server` has an in-process scheduler, distributed-lock option,
and crawler execute/status/health/stop/data endpoints. AutoForge already owns
durable Jobs, Outbox delivery, Airflow generation, worker leasing, and control
plane persistence. The missing unit is the reusable contract that maps an
external trigger to an idempotent durable Job without making an in-process
timer the source of truth.

Keep the canonical news record, idempotent persistence, `news_index` handoff,
delayed-retry contract, and generated log collection unchanged.

Do not add another provider, a retry framework, RAG reranking, or external alert
channel in this slice. The next change should be limited to the existing
durable-job/trigger path and its focused tests.
