# Next Task

## Next executable unit: MySQL HA generated-application acceptance

OWNERSHIP: AutoForge local-environment generation and integration validation

Extend `scripts/verify_mysql_runtime.py --mysql-mode ha` only. Start the
generated application after the existing migration and Router checks, then prove
its health check remains healthy while the verifier performs the current primary
stop, Router writer retry, and node rejoin sequence. Keep the scope to the
disposable verifier; do not add production deployment behavior or specification
fields.
