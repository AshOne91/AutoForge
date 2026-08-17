# Next Task

## Next executable unit: MySQL Operator Kubernetes specification contract

OWNERSHIP: AutoForge specification validation and Kubernetes generation

Add a separate opt-in Kubernetes MySQL Operator profile to the specification.
Require an Operator bootstrap Secret reference, cluster name, member count,
Router replica count, StorageClass and PVC size. Keep application runtime URLs
in the existing Kubernetes Secret. Do not render manifests in this unit.
