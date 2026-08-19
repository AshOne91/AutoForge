# Next Task

## Next executable unit: define role-specific generated service composition

The default standalone profile and the generated HA runtime proofs for Redis
Cluster, PostgreSQL Patroni/HAProxy, RabbitMQ, and the two-scheduler Airflow
profile are verified. The next bounded unit is to make the existing
role-specific composition intent explicit in the generated contract: preserve
the current API/worker/scheduler separation, expose only the selected roles,
and verify one generated profile without changing runtime behavior. Do not
expand this into multi-host deployment or new service types.
