# Next Task

## Next executable unit: verify concurrent idempotent request remains in progress

Extend the post-failover HTTP probe with a fixture handler held behind an async
event. While its first request owns a pending claim, send the same key and body
again and verify the generated route returns 409 without a second handler call.
Release the first request and verify it completes once. Reuse the promoted
Sentinel master and current probe container; do not add queueing, automatic retry,
consumer-domain policy, or a new durability guarantee.
