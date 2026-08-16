# Next Task

## Next executable unit: verify the OpenSearch observability backend path

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: Filebeat now mounts the generated `../logs` and config paths correctly;
Elasticsearch indexed the KIS JSON logs and returned `/health` records through
the generated data stream. Central Elasticsearch and Kibana use `49600`/`49601`.

Validate the selectable OpenSearch path with its own project-owned port block
and the same persisted log contract. Keep collector security, multi-host
storage, and production backup/restore outside this unit.
