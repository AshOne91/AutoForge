# Next Task

## Next executable unit: verify generated request replay through Redis Sentinel failover

The generated request-replay adapter shares the Redis Sentinel client with the
verified session-store lifespan. Add one opt-in Docker drill that claims a replay
key before the primary changes, then completes and reads that replay record after
the same provider reaches the new master. Preserve idempotency semantics; do not
add HTTP endpoint or consumer-domain policy.
