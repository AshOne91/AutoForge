# Next Task

## Next executable unit: verify failed idempotent handler releases its claim

Extend the post-failover HTTP probe with a new idempotency key whose first handler
call raises. Verify the generated route aborts that pending claim, then replace
the handler with a successful fixture and retry the same key and body once.
Reuse the promoted Sentinel master and current probe container; do not add
automatic retry, consumer-domain policy, or a new durability guarantee.
