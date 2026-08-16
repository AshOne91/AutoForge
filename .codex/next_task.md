# Next Task

## Next executable unit: verify generated log collector ingestion

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: The Task Scheduler task and reboot recovery are verified. The
application `/app/logs` bind mount retains JSON lifecycle and request records
through an application restart.

Run the smallest generated Filebeat/ELK or OpenSearch ingestion check against
the persisted `logs/` directory. Keep multi-host storage, Linux/AWS bootstrap,
and backup/restore outside this unit.
