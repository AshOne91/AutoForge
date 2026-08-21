# Next Task

## Next executable unit: automate domestic daily candle collection

Add one validated Durable Job type that accepts a six-digit domestic stock code,
calls the existing KIS daily-candle client, and persists through the existing
`market_history` handler. Reuse the generated Durable Job, worker, token, Redis,
database, logging, and idempotent candle-ID contracts. Prove the handler with
fakes and keep all live KIS calls opt-in. Do not add order, portfolio, strategy,
or arbitrary historical pagination behavior.
