# Next Task

## Next executable unit: Provider-selected Kubernetes database contract

OWNERSHIP: deployment-provider selection; AutoForge follows after selection

Before generating Kubernetes database resources, select one concrete provider
target (for example a managed database or a supported Kubernetes operator) and
define its placement, persistent storage, backup/restore, Router exposure, and
credential-rotation guarantees. Until then, keep the existing provider-owned
Secret URL boundary and do not generate a database `StatefulSet`.
