# Next Task

## Next executable unit: deliver KIS in-app notification hints through realtime

Implement one user-owned KIS vertical slice under ADR-0004: application
lifespan owns the generated backplane listener; an authenticated WebSocket may
subscribe only to the caller's notification channel; the account-shard message
worker publishes only a minimal notification ID/user ID hint after its durable
transaction commits. Verify with generated fakes and focused HTTP/WebSocket or
worker tests. The existing notification read API remains the recovery path, and
no durable Outbox/Inbox or notification persistence contract changes.

Do not add email, SMS, webhooks, automatic orders, or default Redis changes in
this unit. Do not run the explicitly opt-in KIS balance integration check.
