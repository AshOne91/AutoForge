# Next Task

## Next executable unit: establish the multi-replica realtime notification contract

The Base Server reference comparison identified realtime delivery as the next
real missing reusable responsibility: KIS has durable account-shard in-app
notifications and a read fallback, while AutoForge's existing realtime hub is
in-process only and makes no multi-replica delivery claim. Establish the
canonical boundary before implementation: durable notification storage and
RabbitMQ remain authoritative, while any Redis Pub/Sub live hint must be
explicitly best-effort and recoverable through the existing notification read
API. Define the necessary topology, lifecycle, reconnection, and user-channel
ownership rules without adding a local-only pseudo-HA implementation.

Do not add email, SMS, webhooks, automatic orders, or default Redis changes in
this unit. Do not run the explicitly opt-in KIS balance integration check.
