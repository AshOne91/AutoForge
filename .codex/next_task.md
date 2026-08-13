# Next Task

## Next executable unit: verify the generated single-host operating profile live

OWNERSHIP: AutoForge environment validation contract, validated through
kis-auto-trading

EVIDENCE: KIS now selects `tooling.single_host`. AutoForge generated a tracked
`deploy/single-host` overlay with Nginx, three application replicas, restart
policy, and a configurable `/app/logs` host bind mount. Docker Compose validates
the merge with `environment/compose.integration.yml` without starting containers.

Run that generated KIS profile under an isolated Compose project with non-source
test environment files and a non-conflicting public port. Verify Nginx `/health`,
three healthy application containers, and a controlled application-container
restart through the proxy; then remove only that isolated project's containers,
network, and volumes. Do not use production credentials or modify the generated
profile for the test. Host bootstrap, off-host backup, TLS, managed Redis, and
multi-host deployment remain later contracts.
