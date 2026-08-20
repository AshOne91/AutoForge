# Next Task

## Next executable unit: run the explicit KIS balance integration check

Only after the operator explicitly enables `KIS_READ_ONLY_BALANCE_INTEGRATION=1`
and provides the required KIS application/account environment values, run the
default-skipped domestic balance integration test once. Report only pass/fail
and test metadata; do not print account identifiers, holdings, account summaries,
or credential values.

Do not run this live request automatically. Do not add persistence, cache,
polling/Durable Jobs, portfolio ownership mapping, or any order behavior before
a separately approved product and data-ownership contract exists.
