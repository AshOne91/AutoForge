# Next Task

## Next executable unit: verify scheduled Airflow execution

The next executable work is in kis-auto-trading.

OWNERSHIP: user-owned scale-out validation script

EVIDENCE: `scripts/verify_scale_out.py` runs the generated Airflow service,
discovers `durable_job_news_collection`, verifies the cancelled wait failure,
and executes the generated DAG through Airflow `dag.test()` with real
TaskInstance/XCom context against a worker-completed `news_index` Job. The
cancellation contract is verified across PostgreSQL, Outbox relay, RabbitMQ,
and the worker.

Exercise the generated schedule/task-run path in an isolated Airflow metadata
run: unpause the DAG explicitly, use a unique logical date so Durable Job
idempotency does not reuse an older run, and keep external news providers
disabled. Reuse the existing API, worker, and Compose helpers; do not alter the
generated DAG.

The shared local `SequentialExecutor` metadata retained prior manual validation
runs and continued retrying them, so the scheduled-trigger helper was not kept
in the repository. Provide an isolated Airflow metadata database/run first;
do not solve this by adding longer polling or direct production-state updates.

Do not add a new scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
