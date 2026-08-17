# Next Task

## Next executable unit: Generated Kubernetes database boundary guide

OWNERSHIP: AutoForge Kubernetes base-server generator and tests

Add one concise explanation to the existing generated Kubernetes README: database
topology is provider-owned, and the generated workload receives only declared
database URLs through the named Secret. Add the smallest focused generator test.
Do not add a database provider, `StatefulSet`, or deployment profile.
