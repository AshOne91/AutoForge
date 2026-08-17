# Next Task

## Next executable unit: generated MySQL migration runtime validation

OWNERSHIP: AutoForge database generator, generated image, migration, and
environment validation contracts

Generate one minimal MySQL project, build its generated image, run its `migrate`
service against disposable MySQL, and verify the Alembic version and generated
table. Preserve the existing PostgreSQL provider and portable schema contracts;
do not add MySQL HA, RabbitMQ, Outbox, or Durable Jobs in this unit.
