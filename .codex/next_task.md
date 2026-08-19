# Next Task

## Next executable unit: verify the generated KIS HA runtime

The default standalone profile and operator endpoint live flow are verified.
Fresh generation from `autoforge.ha.yaml` now passes validation and produces a
matching Redis Cluster provider and environment contract. The next bounded
unit is a disposable runtime check of that generated HA workspace: start its
Redis Cluster and application, verify session login/read, and exercise one
primary failover without changing the Identity or operator authorization
contract. The historical `compose.integration.yaml` is not the runtime target.
