# Next Task

## Next executable unit: Airflow durable-job cancellation validation

The next executable work is in AutoForge.

OWNERSHIP: generated local environment and durable-job DAG contract

EVIDENCE: the local KIS integration environment now verifies generated
Bearer-token cancellation across PostgreSQL, Outbox relay, RabbitMQ, and the
worker. `requested` Jobs transition to `cancelled`; duplicate cancellation is
idempotent; an already delivered message cannot invoke a cancelled Job's
handler because worker claim is atomic.

Run a generated Airflow DAG against the same local durable-job API. Verify that
the status-polling task reports a cancelled job as a controlled DAG failure,
rather than retrying it or invoking a handler. Do not change cancellation into
an attempt to reverse a completed external side effect.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
