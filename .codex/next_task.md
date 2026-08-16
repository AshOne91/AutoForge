# Next Task

## Next executable unit: verify Filebeat ingestion after replica restart

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, the wheel imports successfully from a fresh
virtual environment, and a real proxied request remains in host JSON logs after
one application replica restarts.

Confirm Filebeat ingests a post-restart application record into the generated
Elasticsearch data stream. Keep centralized retention policy and production
backup/restore outside this unit.
