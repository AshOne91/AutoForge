# Next Task

## Next executable unit: verify the generated distributed lock through Redis Sentinel failover

The generated distributed-lock adapter already accepts Redis Sentinel runtime
settings, and the local Sentinel profile has a verified primary/replica/quorum
topology. Add one opt-in Docker drill that acquires and releases a lock before
and after the primary changes. Preserve the existing lock contract and do not
add fencing, queueing, or consumer-domain policy.
