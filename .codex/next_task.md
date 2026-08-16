# Next Task

## Next executable unit: verify bootstrap after Docker restart

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; and the live KIS bootstrap
reached healthy replicas with `/health` `200`.

Restart Docker Desktop (or the host) and run the generated bootstrap again,
then verify the proxy health endpoint and replica recovery. Keep this as an
operational verification unit; do not change runtime allocation or deployment
topology.
