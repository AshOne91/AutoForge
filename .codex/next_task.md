# Next Task

## Next executable unit: verify generated application health across PostgreSQL HA failover

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: AutoForge generates an optional local three-node Patroni PostgreSQL
cluster with a three-member etcd DCS and HAProxy at the existing `postgres:5432`
writer endpoint. KIS's isolated generated-environment check verifies migration,
one leader/two streaming replicas, HAProxy writer recovery after leader loss, and
the stopped node rejoining as a replica.

Extend that isolated check only after its non-database dependencies are made
healthy: start the generated application, stop the current Patroni leader, wait
for HAProxy promotion, and confirm the application health endpoint recovers
without rebuilding the application container.

Do not add read routing, a production database deployment framework, backup
automation, or unrelated service orchestration in this slice.
