# Next Task

## Next executable unit: define the first reusable service-composition slice

The next executable work spans AutoForge and kis-auto-trading.

OWNERSHIP: AutoForge generation contract, validated through kis-auto-trading

EVIDENCE: KIS now runs independent API, Outbox relay, profile-event worker,
durable-job worker, Airflow, and observability services. The Roadmap still lacks
the reusable AutoForge contract that describes independently deployable service
composition with explicit configuration, lifecycle, health, and Event/Queue
boundaries.

Trace the existing generated environment and KIS-owned override boundaries. Add
only the smallest specification and generation contract that can express one
existing worker service without changing current API, Outbox, or Durable Job
ownership. Validate it through one generated KIS service slice.

Do not introduce a generic service framework, broker cluster, or unrelated
deployment abstraction in this slice.
