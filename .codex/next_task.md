# Next Task

## Next executable unit: verify generated PostgreSQL HA runtime

The default standalone profile and operator endpoint live flow are verified.
Fresh HA generation and the Redis Cluster session failover drill are also
verified. The next bounded unit is the existing disposable PostgreSQL HA drill:
start the generated Patroni/HAProxy stack, verify the writer contract and
application health, stop the active leader, and confirm replacement-writer
recovery. The historical `compose.integration.yaml` is not the runtime target.
