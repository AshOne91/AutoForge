# Next Task

## Next executable unit: Control Plane deployment-provider selection

OWNERSHIP: AutoForge owns the provider-neutral executor, image, Compose profile,
and Kubernetes runtime manifest. The deployment owner must select the concrete
production provider that invokes the executor and supplies PostgreSQL storage,
secrets, backup, restore, and rollout control.

Select one explicit Control Plane deployment provider (for example a Kubernetes
operator workflow or a managed PostgreSQL deployment workflow), then define its
pre-rollout invocation of `migrate-control-plane`, Secret binding, backup and
restore responsibilities, and failure handoff. Do not add application-startup
migration, Kubernetes Job, PostgreSQL StatefulSet/PVC, provider SDK, retry
policy, rollback policy, or generated schema tooling before that provider is
chosen.
