# Next Task

## Next executable unit: generate a Kubernetes durable-job-worker Deployment

The manual KIS `market_price_snapshot` job is the concrete workload that now
needs a separate runtime process: it uses RabbitMQ, the global automation
database, the existing worker entrypoint, and `durable_job_worker` runtime
environment targets. Compose already delivers those inputs, but the generated
Kubernetes base-server output currently deploys only the application process.

Add the smallest generated worker Deployment using the existing durable-job and
runtime-environment contracts. Reuse the current image, generated worker script,
database/secret bindings, RabbitMQ dependency, probes, labels, and replica
settings where their contracts already apply. Do not add a generic application
module-selection field, a new financial schedule, or a new consumer-owned
workflow. Verify the generator output and regenerated KIS manifest; no live KIS
credentials or job execution are required.
