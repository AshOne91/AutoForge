# Next Task

## Next executable unit: prove the scheduled daily-candle path

Run the generated `domestic_daily_candle_collection` Airflow DAG in an isolated
local Compose project with a deterministic local KIS HTTP stand-in and the
deployment-owned stock-code payload. Prove that Airflow creates the Durable Job
and that the existing Outbox/RabbitMQ/worker path persists one candle readable
through the operator GET. Clean up every disposable resource afterward. Do not
call live KIS, add another scheduler abstraction, or start portfolio/order work;
explicit brokerage-account ownership must be established before portfolio
persistence.
