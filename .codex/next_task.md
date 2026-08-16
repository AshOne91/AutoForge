# Next Task

## Next executable unit: verify observability endpoint visibility

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, the wheel imports successfully from a fresh
virtual environment, and a post-restart proxied request appears exactly once
in the Elasticsearch `filebeat-*` data stream.

Confirm the generated Elasticsearch and Kibana endpoints expose the ingested
observability data using their declared `49600`/`49601` ports. Keep centralized
retention policy and production backup/restore outside this unit.
