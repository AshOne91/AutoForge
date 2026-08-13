# Next Task

## Next executable unit: define the durable worker readiness boundary

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: the first slice now makes the durable-job worker restart policy
explicit in `ApplicationSpec` and validates it through generated KIS Compose.
Readiness is still represented only by Compose dependency conditions; the worker
has no explicit health contract.

Trace the existing worker entrypoint and generated environment. Add only the
smallest readiness contract for this worker without changing current API,
Outbox, or Durable Job ownership. Validate it through one generated KIS service
slice.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
