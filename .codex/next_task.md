# Next Task

## Next executable unit: verify generated log continuity through the proxy

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff and wheel/sdist builds pass, the wheel imports successfully from a fresh
virtual environment, and disposable Compose checks confirm three healthy
replicas behind Nginx with forwarded headers.

Send a proxied request through the generated runtime and confirm the
application's persisted JSON log records retain the request identity without
loss across a container restart. Keep centralized log shipping and production
retention policy outside this unit.
