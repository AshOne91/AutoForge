# Next Task

## Next executable unit: audit single-host profile completion

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; the live bootstrap reached
healthy replicas with `/health` `200`; the registered Task Scheduler job
returned `0` after reboot; the host log bind mount retained recent files; and
the live drill produced checksummed identity and shard dumps outside the repo.
The identity dump restored six public tables and both account shards restored
eight public tables each into disposable Spilo targets.

Review the single-host operating profile against its current roadmap items:
durable volumes, log retention, backup/restore evidence, health checks, and
operator recovery. Record only concrete remaining gaps; do not add speculative
infrastructure in this audit.
