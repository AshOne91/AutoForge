# Next Task

## Next executable unit: single-host HA profile reconciliation

Before any cloud or multi-host provider work, verify that the existing AutoForge
single-host generators can reproduce the KIS HA topology on one physical host as
separate Docker logical nodes. Keep the running lightweight KIS profile intact;
use an isolated Compose project for the drill.

Compare the generated KIS output from `autoforge.ha.yaml` with the declared
single-host contract: Nginx public entry point, application replicas, PostgreSQL
HA writer endpoint, Redis Cluster, RabbitMQ cluster, and their stable consumer
connection contracts. Run the smallest disposable core-HA validation that proves
the generated topology starts and recovers one declared node without changing
the active lightweight profile. Fix a generator defect in AutoForge only if the
generated artifact or its verification disagrees with that contract.

Do not select a cloud deployment provider, add Kubernetes migration resources,
or replace the active lightweight profile during this unit. Those are later
deployment concerns after the local logical-node baseline is reproducible.
