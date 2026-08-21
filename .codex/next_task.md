# Next Task

## Next executable unit: verify generated Redis Cluster key-value storage

Add an opt-in Docker drill for the existing generated `KeyValueStore` Redis
Cluster adapter. It must set/get/delete a value through generated multi-startup
node settings, stop one Redis primary, wait for failover, and prove a newly
written value remains accessible. Reuse the existing Redis Cluster generator;
do not add Sentinel behavior, cache invalidation policy, or a provider-specific
topology.
