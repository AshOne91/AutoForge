# Next Task

## Next executable unit: verify bootstrap collision failure

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: the read-only `validate-ports` command is implemented and tested;
the generated Windows bootstrap now checks the fully resolved Compose JSON;
the current KIS configuration passes with five published ports.

Use a disposable Compose configuration with an intentional duplicate published
port to prove the bootstrap preflight fails before container startup. Keep this
as a verification-only unit; do not change runtime allocation or deployment
topology.
