# Next Task

## Next executable unit: verify Airflow successful-job completion

The next executable work is in kis-auto-trading.

OWNERSHIP: user-owned scale-out validation script

EVIDENCE: `scripts/verify_scale_out.py` now runs the generated Airflow service,
discovers `durable_job_news_collection`, and verifies its wait callable turns
a cancelled Job into a controlled failure. The durable Job cancellation contract
is verified across PostgreSQL, Outbox relay, RabbitMQ, and the worker.

Extend the same script with one successful durable-job fixture and verify that
the Airflow wait task returns normally after the worker completes it. Reuse the
existing API, worker, and Compose helpers; do not alter the generated DAG.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
