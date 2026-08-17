# Next Task

## Next executable unit: KIS single-host bootstrap rebuild verification

OWNERSHIP: AutoForge single-host generator; KIS generated deployment overlay.

Run the generated Windows single-host bootstrap after the RabbitMQ cluster
regeneration. Verify it builds the current application image, starts the
declared long-running profile without a stale-image dependency, and restores
the Nginx health endpoint. Do not change deployment configuration unless this
operator-level check proves a concrete generator defect.
