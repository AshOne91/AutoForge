# Next Task

## Next executable unit: build the consumer runtime image from the artifact

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, and the wheel imports successfully from a
fresh virtual environment.

Build the consumer runtime image using the generated package contract and run a
health check. Keep production deployment changes and image publication outside
this unit.
