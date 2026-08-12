# Next Task

## Next executable unit: automate Airflow cancellation verification

The next executable work is in kis-auto-trading.

OWNERSHIP: user-owned scale-out validation script

EVIDENCE: the local KIS integration environment now runs the generated
Airflow service, discovers `durable_job_news_collection`, and verifies its
wait callable turns a cancelled Job into a controlled failure. The durable
Job cancellation contract is already verified across PostgreSQL, Outbox relay,
RabbitMQ, and the worker.

Extend the existing `scripts/verify_scale_out.py` with the smallest Docker
assertion that verifies Airflow DAG discovery and the cancelled wait path. Reuse
the script's existing local Compose command helper; do not create a second test
framework or alter the generated DAG.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
