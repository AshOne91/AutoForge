# Next Task

## Next executable unit: install and import the consumer package artifact

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is installed in the active validation environment;
durable handler and worker tests pass, the full KIS suite reports `33 passed`,
Ruff passes, and wheel/sdist artifacts build successfully.

Install the generated wheel into a clean temporary environment and import the
application package. Keep runtime service deployment and dependency upgrades
outside this unit.
