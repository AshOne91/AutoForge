# Next Task

## Next executable unit: define the Signal delivery execution boundary

Before delivering a pending global SignalDeliveryIntent, determine the one
consumer-owned KIS execution boundary that can call an existing generated
notification, email, or SMS contract without duplicating the current
Outbox/Inbox transport. Define the required claim, expiry, retry, idempotency,
and operator-observability guarantees before adding an external side effect.

Do not select a live provider, send a notification, place an order, or change
default Redis topology in this unit. Do not run the explicitly opt-in KIS
balance integration check.
