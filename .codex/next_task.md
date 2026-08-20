# Next Task

## Next executable unit: generate and verify a local Memcached KeyValueStore profile

When `tooling.key_value_store.backend: memcached` is selected, generate a local
Memcached Compose service with a health check and the matching application
environment contract. Verify generation deterministically and add one opt-in
container runtime drill.

Do not change the KIS default Redis specification, treat Memcached as a
replacement for Redis SessionStore or DistributedLock, or run the explicitly
opt-in KIS balance integration check automatically.
