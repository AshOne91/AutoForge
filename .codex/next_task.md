# Next Task

## Next executable unit: MySQL HA deployment-provider boundary

OWNERSHIP: AutoForge local-environment generation and integration validation

Assess the existing local MySQL HA contract against the chosen deployment target
without generating manifests yet. Identify the required provider-owned inputs
(node placement, persistent storage, backups, and secret delivery) and keep the
current local Docker generator unchanged. Record only a bounded deployment
boundary that can later drive a Kubernetes or managed-service profile.
