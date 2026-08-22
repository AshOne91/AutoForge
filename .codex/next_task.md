# Next Task

## Next executable unit: verify remaining single-worker recovery boundaries

The active Roadmap delivery gate permits only reusable service and local logical
HA work. Durable Job Worker replica safety is now implemented and verified.
Use the same generated HA workspace to prove that the intentionally single
Outbox relay and generic message worker each become healthy, can be stopped,
and return healthy after explicit restart. Do not scale either service: their
at-least-once contracts still require consumer-owned idempotency. Do not add KIS
business-domain behavior.
