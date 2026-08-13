# Next Task

## Next executable unit: document and validate manual Patroni leaderless recovery

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: The isolated generated-environment check verifies a six-node Redis
restart, idempotent cluster initialization, `cluster_state:ok`, complete slot
coverage, and unchanged application health. A simultaneous shutdown of all
Patroni nodes leaves all members as replicas without a writable leader.

Define the bounded operator procedure for a leaderless local Patroni cluster:
inspect member state and DCS, select an explicitly named failover candidate,
perform the manual failover, and verify HAProxy writer recovery and replica
rejoin. Do not automate candidate selection or claim zero data loss.

Do not add Redis Sentinel/managed Redis deployment, new session semantics, or
unrelated service orchestration in this slice.
