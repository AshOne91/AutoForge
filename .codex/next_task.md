# Next Task

## Next executable unit: implement opt-in Airflow scheduler HA

OWNERSHIP: AutoForge specification, validation, and local-environment generator

DECISION: [ADR-0001](../docs/adr/0001-local-airflow-scheduler-ha.md) selects
`airflow_scheduler_replicas >= 2`, PostgreSQL HA metadata storage, and
`LocalExecutor` for single-host scheduler HA. Existing Durable Job API
idempotency remains the second execution boundary.

Implement the new Local Environment specification field and validate that
replica counts above one require local environment, Durable Jobs, and
`postgres_mode: ha`. Preserve the default one-scheduler `SequentialExecutor`
profile and do not change RabbitMQ, Durable Job, or PostgreSQL topology.

Generate two named scheduler containers for the first HA profile, a shared
user-owned `AIRFLOW_FERNET_KEY` reference, `LocalExecutor`, and independent
scheduler healthchecks. Verify generator output first, then an isolated
generated KIS runtime: stop one scheduler, trigger a new logical date through
the surviving scheduler, confirm one Durable Job, and verify the stopped
scheduler rejoin. Do not add Celery/Kubernetes executors, webserver replicas,
triggerer replicas, host ports, or cloud deployment in this unit.
