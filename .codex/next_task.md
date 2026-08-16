# Next Task

## Next executable unit: define the single-host backup drill

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; the live bootstrap reached
healthy replicas with `/health` `200`; the registered Task Scheduler job
returned `0` after reboot; and the host log bind mount retained recent files.

Define a minimal, recoverable backup/restore drill for the generated single-host
profile, starting with the host log volume and generated database backup
artifacts. Do not delete live data or change runtime topology in that unit.
