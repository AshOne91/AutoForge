# Next Task

## Next executable unit: verify idempotency conflict after Redis Sentinel failover

Extend the existing opt-in generated HTTP drill with a request body. After the
same completed response is replayed through the promoted master, reuse the same
idempotency key with a changed body and verify the generated route returns 409
without invoking its handler. Reuse the current Sentinel topology and probe
containers; do not add retry, consumer-domain policy, or a new durability
guarantee.
