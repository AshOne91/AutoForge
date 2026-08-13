# Next Task

## Next executable unit: verify generated application continuity across Redis Cluster failover

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: The generated local environment already creates a six-node Redis
Cluster and the KIS scale-out check verifies slot coverage, primary/replica
promotion, and application health after a Redis node failure.

Extend that check to record the application container ID before the Redis
primary failure and confirm the same container becomes healthy after its
replica is promoted, without rebuilding or recreating the application.

Do not add Redis Sentinel/managed Redis deployment, new session semantics, or
unrelated service orchestration in this slice.
