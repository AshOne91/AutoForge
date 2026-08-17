# Next Task

## Next executable unit: MySQL Operator InnoDBCluster manifest generation

OWNERSHIP: AutoForge Kubernetes base-server generator and tests

Render one generated `InnoDBCluster` manifest only when the opt-in profile is
enabled. Include the declared bootstrap Secret, member and Router counts, and
PVC template. Keep the application runtime Secret separate and do not install
the Operator, apply resources, or add backup policy in this unit.
