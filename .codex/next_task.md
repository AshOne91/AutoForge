# Next Task

## Next executable unit: MySQL HA primary-failure acceptance

OWNERSHIP: AutoForge local-environment generation and integration validation

Extend `scripts/verify_mysql_runtime.py --mysql-mode ha` only. After its current
Router-backed migration and schema checks, stop the initial primary, retry one
writer-path operation through `mysql:6446`, restart the stopped node, and verify
the cluster is healthy again. Keep the scope to the disposable verifier; do not
add production deployment behavior or new specification fields.
