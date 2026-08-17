# Next Task

## Next executable unit: define the opt-in Airflow HA generation contract

OWNERSHIP: AutoForge specification, validation, and local-environment generator

EVIDENCE: the opt-in RabbitMQ cluster mode now preserves the existing
`RABBITMQ_URL` endpoint while generating three broker nodes, HAProxy, quorum
event/dead-letter queues, and a one-node stop/rejoin validation. The local
result is broker-process recovery on one Docker host, not host-level HA.

The current Airflow local runtime has one scheduler and one webserver. RabbitMQ
and PostgreSQL topology must not be changed by this unit.

Define the smallest explicit opt-in Airflow HA contract: metadata database
requirements, executor constraints, scheduler count, scheduler health, and a
two-scheduler failure drill. Preserve the existing single-scheduler default and
defer webserver replicas, proxy/Ingress, Kubernetes placement, and cloud
deployment to later deployment contracts.
