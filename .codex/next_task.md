# Next Task

## Next executable unit: run the generated bootstrap smoke test

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap checks the fully resolved Compose JSON;
an intentional `49999` collision fails before `up`; and AutoForge reports
`489 passed, 6 skipped`.

Run the generated Windows bootstrap once with the KIS single-host profile after
Docker Desktop is available, then verify the proxy health endpoint and the
preflight log path. Keep this as an operational verification unit; do not change
runtime allocation or deployment topology.
