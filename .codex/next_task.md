# Next Task

## Next executable unit: restore host validation dependency parity

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `news_collection` succeeded, its generated `news_index` follow-up
succeeded, and ten Yahoo articles were indexed into OpenSearch. Host-side
durable handler tests cannot collect because the active `autoforge` environment
does not contain `yfinance`.

Align the developer validation environment with the generated KIS dependency
contract, then rerun the durable handler tests. Keep unrelated dependency
upgrades and production deployment changes outside this unit.
