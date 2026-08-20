# Next Task

## Next executable unit: define the Signal domain boundary

Specify one consumer-owned Signal use case that composes existing
Messaging/Outbox, Realtime, and (when needed) LLM or SMS delivery. Add no new
generic transport until the signal payload, subscriber identity, and delivery
guarantee are explicit.

Do not create a generic signal transport, change the KIS default Redis
specification, or run the explicitly opt-in KIS balance integration check.
