# Next Task

## Next executable unit: verify Airflow task-run completion

The next executable work is in kis-auto-trading.

OWNERSHIP: user-owned scale-out validation script

EVIDENCE: `scripts/verify_scale_out.py` runs the generated Airflow service,
discovers `durable_job_news_collection`, verifies the cancelled wait failure,
and executes the generated `trigger_job` plus `wait_for_job` functions against a
real worker-completed `news_index` Job. The cancellation contract is verified
across PostgreSQL, Outbox relay, RabbitMQ, and the worker.

Run those generated callables through an Airflow task execution context, keeping
the deterministic `news_index` path and avoiding external news providers. Reuse
the existing API, worker, and Compose helpers; do not alter the generated DAG.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
