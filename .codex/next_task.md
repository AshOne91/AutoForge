# Next Task

## Next executable unit: distinguish local recovery from production Redis HA

OWNERSHIP: AutoForge environment validation contract, validated through
kis-auto-trading

EVIDENCE: The isolated generated-environment check now verifies a six-node
Redis restart, full Compose network recreation with persisted Redis volumes,
and manual recovery of an intentionally leaderless local Patroni cluster using
an explicitly named candidate. It proves only a single-host Docker recovery
path.

Define the smallest production-boundary decision for managed Redis topology:
whether the first deployment target requires managed Redis Cluster, Sentinel,
or no generated production Redis manifest. Preserve the current local Compose
contract and do not add a provider-specific deployment implementation until a
consumer and provider are selected.
