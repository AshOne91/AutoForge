# Next Task

## Next executable unit: isolate Airflow scheduler task validation

The next executable work is in kis-auto-trading.

OWNERSHIP: AutoForge local-environment validation contract

EVIDENCE: AutoForge now renders `airflow-init`, `airflow-webserver`, and
`airflow-scheduler`; KIS runs the same lifecycle in its user-owned scale-out
profile. The scheduler process is live, but a shared Airflow metadata database
cannot safely distinguish a test-triggered cron run from independently due runs.

Create a dedicated test metadata database or isolated Compose project for one
Airflow scheduler-trigger test. It must start with an empty Airflow metadata
database, use a unique logical date, cancel only the known test Job through the
internal API, and remove only that test run's metadata. Do not substitute the
KIS-owned `compose.integration.yaml`; it is a richer validation profile, not
generated output.

Do not add another scheduler, provider, retry framework, RAG reranking, or
external alert channel in this slice.
