# Next Task

## Next executable unit: durable-job cancellation contract

The next executable work is in AutoForge.

OWNERSHIP: AutoForge architecture and generation contract

EVIDENCE: AutoForge already generates a token-protected trigger/status API and
an Airflow DAG whose data-interval run key reaches the durable-job repository.
KIS now runtime-verifies those generated endpoints. `base_server` also exposes
an operator stop endpoint, but AutoForge has no durable-job cancellation state
or API contract yet.

Define the smallest cancellation boundary: which requested or running Jobs may
be cancelled, how a worker observes it, what remains in Outbox, and what status
the GET endpoint returns. Do not imply that cancellation can undo an already
completed external side effect.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
