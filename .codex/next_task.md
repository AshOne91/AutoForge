# Next Task

## Next executable unit: implement the single-host operating profile

OWNERSHIP: AutoForge environment validation contract, validated through
kis-auto-trading

EVIDENCE: The generated Kubernetes manifest injects `REDIS_CLUSTER_URL` from a
Secret and intentionally contains no Redis server image or workload. The local
Compose Cluster already verifies container-level Redis recovery on one Docker
host, but it is still an integration profile rather than an operator-facing
deployment profile.

Define and generate one self-hosted single-host operating slice with explicit
restart policy, named-volume ownership, secret injection, health checks, log
paths, and operator start/stop instructions. Keep it separate from the disposable
integration profile. Do not infer AWS, managed Cluster, Sentinel, or an
in-cluster Redis operator from the local topology; those are later provider
contracts.
