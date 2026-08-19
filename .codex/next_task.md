# Next Task

## Next executable unit: verify generated RabbitMQ HA runtime

The default standalone profile and operator endpoint live flow are verified.
Fresh HA generation, Redis Cluster session failover, and PostgreSQL
Patroni/HAProxy failover are verified. The next bounded unit is the generated
RabbitMQ HA drill: start the three-node quorum profile, verify the broker
health and application dependency path, stop one broker, and confirm the
remaining cluster recovers without changing the Identity or operator contract.
The historical `compose.integration.yaml` is not the runtime target.
