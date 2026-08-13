# Next Task

## Next executable unit: verify Redis cluster readiness semantics

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the generated worker and outbox relay verify real RabbitMQ
connections through Compose healthchecks. KIS generation, static Compose
validation, focused tests, isolated live startup, and a RabbitMQ restart all
pass with both services healthy/reconnected.

KIS application health now probes internal PostgreSQL and Redis TCP reachability;
a direct probe fails when PostgreSQL is stopped and succeeds after recovery.
Trace the existing generated Redis Cluster initialization and session provider,
then verify whether TCP probes are sufficient or whether cluster-state readiness
needs a separate generated check. Do not change the public health API or session
ownership until the current cluster contract is proven insufficient.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
