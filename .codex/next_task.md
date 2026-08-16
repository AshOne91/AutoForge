# Next Task

## Next executable unit: verify proxy routing to the replacement replicas

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, the wheel imports successfully from a fresh
virtual environment, and a disposable Compose project reports three healthy
replicas from the separately tagged runtime image.

Put the generated Nginx proxy in front of the disposable three-replica image,
verify repeated `/health` responses and forwarded request metadata, then leave
the current production-like services intact. Keep image publication and
deployment changes outside this unit.
