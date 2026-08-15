# Next Task

## Next executable unit: verify generated single-host Nginx restart recovery

OWNERSHIP: AutoForge environment validation contract, validated through
kis-auto-trading

EVIDENCE: The generated KIS `deploy/single-host` overlay now runs under an
isolated Compose project. It proves Nginx `/health`, three healthy application
replicas, and recovery after restarting one application container. Nginx itself
has `restart: unless-stopped`, but that recovery path is not yet exercised.

Extend the existing KIS isolated verification script only enough to restart the
generated Nginx container and recheck the public `/health` path. Keep its
ephemeral project, local-only ports, and cleanup boundary unchanged. Do not
claim host reboot recovery, TLS, off-host backup, managed Redis, or multi-host
deployment from this service-container check.
