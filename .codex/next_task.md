# Next Task

## Next executable unit: define application dependency readiness

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker and outbox relay verify real RabbitMQ
connections through Compose healthchecks. KIS generation, static Compose
validation, focused tests, isolated live startup, and a RabbitMQ restart all
pass with both services healthy/reconnected.

KIS application health also stays healthy across a PostgreSQL restart, but the
current `/health` contract checks HTTP process liveness only. Trace existing
generated application startup and database/session providers, then add only the
smallest explicit readiness contract if it can be expressed without changing
the public health API or transaction ownership. Validate through one generated
KIS service slice.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
