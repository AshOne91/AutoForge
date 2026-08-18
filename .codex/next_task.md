# Next Task

## Next executable unit: single-host Redis primary-failover reconciliation

Using a fresh generated KIS HA workspace, identify the elected Redis Cluster
primary for one application session key, stop only that primary, and verify its
replica promotion, cluster slot health, application continuity, and rejoin after
restart. Reuse the current generated service names and connection contracts; do
not hand-edit generated Compose artifacts or replace the running lightweight
profile.

Do not select a cloud deployment provider, add Kubernetes migration resources,
or replace the active lightweight profile during this unit. Kubernetes
provider-store connectivity is a later concern after the Docker logical-node
failover path is reproducible.
