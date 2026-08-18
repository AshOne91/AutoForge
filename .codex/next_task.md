# Next Task

## Next executable unit: scaffold-preservation ownership drill

Use a disposable KIS workspace to prove the intended ownership boundary for one
generated application module: AutoForge generates its infrastructure and
scaffolded domain-handler boundary, while an existing consumer-owned handler is
preserved on regeneration. Confirm the manifest ownership and inspect only the
affected generation plan, handler, and generated route. Do not implement domain
logic merely to make an empty generated workspace behave like the KIS product,
and do not hand-edit generated-owned artifacts.

This check must keep the generated skeleton and consumer business implementation
as separate concerns. It does not select a cloud provider or add Kubernetes
stateful-provider resources.
