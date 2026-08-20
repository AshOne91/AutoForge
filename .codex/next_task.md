# Next Task

## Next executable unit: expose pending SignalDeliveryIntent records safely

In KIS, add one operator-token-protected, read-only lookup for pending global
SignalDeliveryIntent records by domestic stock code. Reuse the generated model,
global session, and existing operator service-token boundary; do not expose
user-private subscription data or change the materialization workflow.

Do not add SMS, email, WebSocket, webhook, automatic order, or default Redis
changes in this unit. Do not run the explicitly opt-in KIS balance integration
check.
