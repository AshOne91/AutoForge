# Next Task

## Next executable unit: materialize Signal intents as in-app notifications

In KIS, introduce an account-sharded generated `InAppNotification` persistence
model and materialize each global SignalDeliveryIntent into it through a new
global Outbox event and account-shard Inbox consumer. Use a deterministic
notification identifier derived from the intent, so RabbitMQ redelivery cannot
create a second in-app record. Keep the global intent immutable and do not
perform an external side effect.

Do not add email, SMS, WebSocket, webhook, automatic order, provider selection,
or default Redis changes in this unit. Do not run the explicitly opt-in KIS
balance integration check.
