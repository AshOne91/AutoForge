# Next Task

## Next executable unit: run the scheduled-ingestion standalone runtime smoke

Start the disposable generated `scheduled_ingestion` integration Compose profile,
wait for its PostgreSQL, RabbitMQ, Airflow, application, relay, and worker health
boundaries, then verify the public application and Airflow endpoints. Tear down
the disposable stack after collecting diagnostics. Do not start the optional RAG
or storage overlays, edit generated-owned output, or reuse preserved consumer
containers and volumes.
