# Next Task

## Next executable unit: add Redis Sentinel support to the generated realtime backplane

Extend the existing Redis Pub/Sub realtime backplane so the already-supported
Redis Sentinel connection mode can provide its master connection instead of
being rejected. Preserve the `RealtimeBackplane` interface and existing
standalone/Cluster behavior. Add focused generation tests and, if the existing
local Sentinel profile can carry it without a new deployment contract, one
opt-in failover delivery drill. Do not add durable queue semantics, user-channel
policy, or consumer-domain notification behavior.
