# Next Task

## Next executable unit: MySQL runtime acceptance automation

OWNERSHIP: AutoForge integration validation and generated-runtime contracts

Add an opt-in integration command that generates one minimal MySQL project, builds
its generated image, runs `migrate` against disposable MySQL, verifies the
Alembic version and generated table, and removes only its owned resources.
Preserve the existing PostgreSQL provider and portable schema contracts; do not
add MySQL HA, RabbitMQ, Outbox, or Durable Jobs in this unit.
