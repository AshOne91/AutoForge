# Next Task

## Next executable unit: verify Airflow trigger-and-wait completion

The next executable work is in kis-auto-trading.

OWNERSHIP: user-owned scale-out validation script

EVIDENCE: `scripts/verify_scale_out.py` runs the generated Airflow service,
discovers `durable_job_news_collection`, verifies the cancelled wait failure,
and proves that its generated wait function observes a real worker-completed
`news_index` Job. The cancellation contract is verified across PostgreSQL,
Outbox relay, RabbitMQ, and the worker.

Invoke the generated `trigger_job` and `wait_for_job` functions together against
the deterministic `news_index` path, so Airflow itself creates the Job before
the real worker completes it. Reuse the existing API, worker, and Compose
helpers; do not alter the generated DAG or invoke external news providers.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
