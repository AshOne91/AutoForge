# Next Task

## Next executable unit: validate generated port collision guards

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, the wheel imports successfully from a fresh
virtual environment, a post-restart request appears exactly once in the
Elasticsearch data stream, and Elasticsearch/Kibana respond on `49600`/`49601`.

Exercise the existing specification validation for overlapping application,
RAG, and observability host-port blocks. Keep deployment topology and dynamic
port allocation outside this unit.
