# Next Task

## Next executable unit: verify recovered KIS scale-out messaging

OWNERSHIP: KIS operator configuration and AutoForge-generated single-host
artifacts

EVIDENCE: the legacy KIS scale-out RabbitMQ profile now has an explicit
`restart: unless-stopped` policy. RabbitMQ was recreated without volume reset;
the durable-job worker, message worker, and Outbox relay recovered, and API
health returned HTTP 200.

The default generated MinIO overlay remains profile-selected at execution. Its
generated `minio-init` task creates `S3_BUCKET` idempotently, and a disposable
KIS consumer workspace passed the actual `autoforge backup` preflight. The KIS
generated README conflict is resolved without overwriting KIS-owned operations
documentation. PostgreSQL HA remains the selected runtime; MySQL is deferred
until a real consumer requirement exists.

Run the focused KIS scale-out verification against the recovered profile and
confirm the durable messaging path remains healthy after RabbitMQ recovery.
Do not change database providers, add scheduling, or introduce new
infrastructure in this unit.
