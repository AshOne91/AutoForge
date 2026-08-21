# Next Task

## Next executable unit: read persisted domestic daily candles

Declare one generated `list_by_stock_code` repository query for
`DomesticDailyCandle`, ordered by trading date descending with a bounded limit.
Regenerate KIS before adding an operator-token-protected GET path that reads only
the global `automation` store and never calls KIS. Verify the generated query,
safe API failure mapping, and a real disposable PostgreSQL round trip. Do not add
arbitrary date-range pagination, order, portfolio, or strategy behavior.
