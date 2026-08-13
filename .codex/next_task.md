# Next Task

## Next executable unit: decide Redis Cluster replica topology

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker and outbox relay verify real RabbitMQ
connections through Compose healthchecks. KIS generation, static Compose
validation, focused tests, isolated live startup, and a RabbitMQ restart all
pass with both services healthy/reconnected.

KIS application health now probes internal PostgreSQL and Redis reachability;
Redis Cluster mode uses `require_full_coverage=True` and `PING`. A live KIS
check shows that stopping `redis-7000` produces `cluster_state:fail` and 5461
failed slots because the generated topology has three masters and zero replicas;
restoring it returns the cluster and application to healthy. Decide the minimum
replica topology required for the target HA baseline before changing the
generator. Do not add failover orchestration or alter session ownership in this
decision slice.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
