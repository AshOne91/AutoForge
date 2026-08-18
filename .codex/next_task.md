# Next Task

## Next executable unit: single-host stateful HA failover reconciliation

Reuse the freshly generated KIS HA workspace and its existing isolated
PostgreSQL HA verifier to prove one stateful failure path: stop the elected
Patroni leader, confirm HAProxy restores the unchanged application writer
contract through a promoted leader, then confirm the stopped member rejoins as
a replica. Keep the running lightweight KIS profile intact and use only the
drill's generated Compose project and volumes.

Do not select a cloud deployment provider, add Kubernetes migration resources,
or replace the active lightweight profile during this unit. Those are later
deployment concerns after the single-host logical-node baseline and its
stateful failover path are reproducible.
