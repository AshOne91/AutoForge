# Next Task

## Next executable unit: establish MySQL local-HA recovery proof

The active Roadmap delivery gate permits only reusable service and local logical
HA work. PostgreSQL, Redis, RabbitMQ, Airflow, application replicas, Durable
Job Worker replicas, and the intentionally single relay/message-worker recovery
boundaries have recorded local proofs. `mysql_mode: ha` currently has generated
InnoDB-cluster and router configuration coverage only. Run an isolated generated
MySQL HA workspace, identify the first real startup or failover gap, and add the
smallest reusable generator or verification change needed for a durable-state
and writer-recovery proof. Do not add KIS business-domain behavior.
