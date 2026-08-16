# Next Task

## Next executable unit: assign the generated ELK host port block

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: Filebeat now mounts the generated `../logs` and config paths correctly;
Elasticsearch indexed the KIS JSON logs and returned `/health` records through
the generated data stream.

Add an explicit project-owned host port block for Elasticsearch and Kibana and
verify it does not collide with the 49400 application block. Keep collector
security, multi-host storage, and production backup/restore outside this unit.
