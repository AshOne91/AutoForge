# Next Task

## Next executable unit: verify a source-compatible database restore

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; the live bootstrap reached
healthy replicas with `/health` `200`; the registered Task Scheduler job
returned `0` after reboot; the host log bind mount retained recent files; and
the live drill produced checksummed identity and shard dumps outside the repo.
The identity dump also restored two core tables into a disposable target after
excluding source-specific archive entries.

Use the same Spilo image, extensions, and roles as the source HA cluster for a
complete restore of one dump, verify expected tables, and remove only that
disposable target afterward. Do not restore over live databases or change
runtime topology.
