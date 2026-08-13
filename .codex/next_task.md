# Next Task

## Next executable unit: verify Redis node restart semantics

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker and outbox relay verify real RabbitMQ
connections through Compose healthchecks. KIS generation, static Compose
validation, focused tests, isolated live startup, and a RabbitMQ restart all
pass with both services healthy/reconnected.

KIS application health now probes internal PostgreSQL and Redis reachability;
Redis Cluster mode uses `require_full_coverage=True` and `PING`. Live KIS
verification reports `cluster_state:ok`, zero failed slots, three known nodes,
and stable healthy checks. Verify the smallest isolated Redis node restart and
confirm the generated application health contract reports the expected state
without changing session ownership or introducing failover orchestration.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
