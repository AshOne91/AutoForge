# Next Task

## Next executable unit: Kubernetes database-provider boundary test

OWNERSHIP: AutoForge Kubernetes base-server generator and tests

Add one focused generator contract test that combines the local MySQL HA profile
with the Kubernetes base-server profile. It must prove that the Kubernetes
manifest still receives declared database URLs only through `secretKeyRef` and
does not emit local Compose or MySQL-cluster resources. Keep both generators and
their public specifications unchanged.
