# Next Task

## Next executable unit: define the Signal domain boundary

Specify one consumer-owned trading Signal use case from the reference flow:
symbol subscription, market-data ownership, signal payload (`symbol`, direction,
price, confidence), subscriber identity, duplicate-suppression key, and
delivery guarantee. Map its output to existing Messaging/Outbox, Realtime, and
(when needed) LLM or SMS delivery. Add no generic Signal transport.

Do not create a generic signal transport, change the KIS default Redis
specification, or run the explicitly opt-in KIS balance integration check.
