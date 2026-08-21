# Next Task

## Next executable unit: prove the regenerated KIS Airflow scheduler boundary

Run the maintained Airflow scheduler verifier against the fresh KIS HA generation.
Prove initialization, DAG visibility, scheduled durable-job delivery, and bounded
scheduler recovery without calling the live KIS API. Preserve the documented
single-host availability boundary and remove disposable resources after the drill.
