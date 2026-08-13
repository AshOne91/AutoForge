# Next Task

## Next executable unit: codify Redis primary failover verification

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: AutoForge now generates a six-node local Redis Cluster with three
primaries, three replicas, named per-node volumes, and multi-node startup URLs.
KIS generation, static Compose validation, focused tests, isolated live startup,
and a `redis-7000` stop/recovery pass. During the stop, `redis-7004` is promoted,
the cluster keeps all 16,384 slots, and the generated application stays healthy.

Turn the demonstrated failover procedure into one isolated KIS runtime
verification: start the generated Redis profile, stop one primary, wait for a
replica promotion and full slot coverage, verify application health, then restore
the node. Keep it separate from broker, Airflow, and external-provider tests.

Do not add failover orchestration, a generic service framework, broker cluster,
or unrelated deployment abstraction in this slice.
