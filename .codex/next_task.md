# Next Task

## Next executable unit: verify Airflow worker-success completion

The next executable work is in kis-auto-trading.

OWNERSHIP: user-owned scale-out validation script

EVIDENCE: `scripts/verify_scale_out.py` runs the generated Airflow service,
discovers `durable_job_news_collection`, and verifies both the cancelled wait
failure and the normal return after a Job is marked `succeeded`. The cancellation
contract is verified across PostgreSQL, Outbox relay, RabbitMQ, and the worker.

Use a bounded local job handler that completes through the real durable-job worker,
then verify Airflow observes `succeeded` without synthetic SQL status mutation.
Reuse the existing API, worker, and Compose helpers; do not alter the generated
DAG or invoke external news providers.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
