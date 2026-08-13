# Next Task

## Next executable unit: verify Redis primary rejoin after Cluster failover

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: The generated local environment creates a six-node Redis Cluster and
the KIS scale-out check now verifies primary/replica promotion, unchanged API
container health, session reads, and a new login after a Redis node failure.

Extend that check to wait for the stopped Redis primary to rejoin as a replica
after it is restarted in cleanup, while preserving the promoted primary and
application health.

Do not add Redis Sentinel/managed Redis deployment, new session semantics, or
unrelated service orchestration in this slice.
