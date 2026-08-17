# Next Task

## Next executable unit: MySQL standalone runtime slice

OWNERSHIP: AutoForge database specification, generator, migration, and
environment validation contracts

Implement the smallest complete MySQL provider slice: generated Compose service,
`asyncmy` DSN and secret boundary, MySQL migration baseline, and disposable
validation. Preserve the existing PostgreSQL provider and portable schema
contracts; do not redesign database generation or add MySQL HA in this unit.
