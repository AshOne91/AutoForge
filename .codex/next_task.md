# Next Task

## Next executable unit: make the local realtime-notification smoke drill reproducible

Add one KIS-local, non-production verification command that reuses the existing
session, RabbitMQ, notification, and WebSocket contracts to prove a durable
notification and its minimal live hint together. Keep runtime values ephemeral,
avoid KIS API calls and external delivery providers, and do not change the
best-effort realtime or fail-closed environment contracts.

The command should be optional and operator-invoked; it must not run on normal
application startup.
