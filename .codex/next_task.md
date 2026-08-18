# Next Task

## Next executable unit: identity-session Redis failover reuse check

Inspect the existing KIS operational verifiers for a user-owned identity flow
that already performs Redis primary failover. Reuse it if present; otherwise add
only the smallest consumer-owned verification that starts from the preserved
identity extension, signs in, stops the elected session-key primary, validates
the existing session through the generated HTTP route, and verifies node rejoin.
Do not add domain behavior or hand-edit generated-owned artifacts.

This is a single-host logical-node validation. It does not select a cloud
provider or add Kubernetes stateful-provider resources.
