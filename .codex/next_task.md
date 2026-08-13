# Next Task

## Next executable unit: record the first production Redis deployment target

OWNERSHIP: AutoForge environment validation contract, validated through
kis-auto-trading

EVIDENCE: The generated Kubernetes manifest injects `REDIS_CLUSTER_URL` from a
Secret and intentionally contains no Redis server image or workload. The local
Compose Cluster remains a single-host validation environment, not a production
deployment choice.

Before adding a provider-specific deployment contract, record the KIS production
target together with the selected Redis offering, availability zone/region
requirements, network boundary, backup/restore objective, and owner of secrets.
Then implement one generated deployment slice for that explicit target. Do not
infer AWS, managed Cluster, Sentinel, or an in-cluster Redis operator from the
local Compose topology.
