# Next Task

## Next executable unit: design the global Signal subscription projection

Define the consumer-owned projection that consumes
`signal.subscription.updated` from account shards and supports lookup by
domestic stock code without treating cross-shard reads as one transaction.
Specify the projection's identity, replay/idempotency behavior, and recovery
path before wiring a Signal consumer to Messaging, Realtime, or Notification.

Do not change the KIS default Redis specification or run the explicitly opt-in
KIS balance integration check.
