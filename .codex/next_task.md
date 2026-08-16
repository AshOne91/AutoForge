# Next Task

## Next executable unit: run consumer lint and package validation

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, and the full KIS suite reports `33 passed`
with the documented cache-disabled command.

Run the declared Ruff check and package build for the consumer without changing
test behavior or production deployment configuration.
