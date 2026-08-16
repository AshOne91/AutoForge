# Next Task

## Next executable unit: verify generated image replacement in Compose

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, the wheel imports successfully from a fresh
virtual environment, and a separately tagged runtime image passes `/health`
with live database and Redis lifespan connections.

Replace only the application image in a disposable Compose validation profile,
verify replica health, then leave the current production-like services intact.
Keep image publication and deployment changes outside this unit.
