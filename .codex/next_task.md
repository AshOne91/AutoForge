# Next Task

## Next executable unit: verify generated Redis Cluster distributed locks

Add an opt-in Docker drill for the existing generated `DistributedLock` Cluster
adapter. It must acquire/release a lock through generated multi-startup-node
settings, stop the lock-owning Redis primary, wait for failover, and prove a new
lock can be acquired and released. Reuse the existing Redis Cluster generator;
do not add Sentinel behavior, Redlock, fencing tokens, auto-renewal, or a
provider-specific topology.
