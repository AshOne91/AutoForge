# Next Task

## Next executable unit: verify generated Airflow scheduler HA runtime

The default standalone profile and operator endpoint live flow are verified.
Fresh HA generation, Redis Cluster session failover, PostgreSQL
Patroni/HAProxy failover, and RabbitMQ three-node recovery are verified. The
next bounded unit is the generated Airflow scheduler HA drill: start the
declared scheduler replicas, verify scheduler health and one DAG trigger, stop
one scheduler, and confirm the survivor continues scheduling. The historical
`compose.integration.yaml` is not the runtime target.
