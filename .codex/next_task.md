# Next Task

## Next executable unit: MySQL 8.4 Router supply-chain proof

OWNERSHIP: AutoForge local-environment generation and integration validation

Identify one reproducible Linux amd64 Router distribution that matches the
generated MySQL 8.4 server image. Prove it can bootstrap against a disposable
three-member single-primary InnoDB Cluster, accept a write through its writer
endpoint, promote a surviving primary after one node stops, and recover the
stopped node. Do not add `mysql_mode: ha` or generated MySQL HA Compose output
until this proof passes.
