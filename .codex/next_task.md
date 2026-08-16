# Next Task

## Next executable unit: restore the backup into a disposable target

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; the live bootstrap reached
healthy replicas with `/health` `200`; the registered Task Scheduler job
returned `0` after reboot; the host log bind mount retained recent files; and
the live drill produced checksummed identity and shard dumps outside the repo.

Restore one dump into a disposable PostgreSQL target, verify expected tables,
and remove only that disposable target afterward. Do not restore over live
databases or change runtime topology in that unit.
