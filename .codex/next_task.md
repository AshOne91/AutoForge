# Next Task

## Next executable unit: define the opt-in RabbitMQ HA generation contract

OWNERSHIP: AutoForge specification, validation, and local-environment generator

EVIDENCE: the KIS legacy scale-out profile now validates restart recovery,
Airflow job paths, RabbitMQ Outbox recovery/DLQ/idempotency, Redis primary
promotion/rejoin, and two-API session/shard behavior. Its RabbitMQ service is
still one broker, so this proves recovery rather than broker-node redundancy.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
KIS consumer workspace passed the actual `autoforge backup` preflight. The KIS
generated README conflict is resolved without overwriting KIS-owned operations
documentation. PostgreSQL HA remains the selected runtime; MySQL is deferred
until a real consumer requirement exists.

Define and test an explicit opt-in local RabbitMQ HA mode while preserving the
default standalone broker and existing `RABBITMQ_URL` consumer contract. The
contract must distinguish local process-level recovery from multi-host HA and
must not change Airflow topology or database providers in this unit.
