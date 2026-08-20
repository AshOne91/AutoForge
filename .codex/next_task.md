# Next Task

## Next executable unit: materialize eligible SignalDeliveryIntent records

In KIS, add the smallest Inbox-backed `signal.created` consumer that reads the
global enabled subscription projection and persists one deterministic pending
delivery intent per eligible subscription before the producer-owned expiry. Use
the generated `SignalDeliveryIntent` repository and existing Outbox/Inbox
transport; keep the initial worker free of external delivery channels.

Do not add SMS, email, WebSocket, webhook, automatic order, or default Redis
changes in this unit. Do not run the explicitly opt-in KIS balance integration
check.
