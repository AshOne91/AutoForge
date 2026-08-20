# Next Task

## Next executable unit: connect the Signal producer to existing delivery

Implement one KIS-owned producer path that accepts a validated SignalEvent and
publishes an existing domain event through Messaging/Outbox. Keep Realtime,
Notification, LLM, and SMS as optional consumers; do not add a generic Signal
transport, market-data master election, or trading-order execution yet.

Do not create a generic signal transport, change the KIS default Redis
specification, or run the explicitly opt-in KIS balance integration check.
