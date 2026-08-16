# Next Task

## Next executable unit: remove the remaining host test warning

OWNERSHIP: AutoForge Kubernetes generator, validated through kis-auto-trading

EVIDENCE: `yfinance` is now installed in the active validation environment;
durable handler and worker tests pass, and the full KIS suite reports `33 passed`.
The only remaining output is a `.pytest_cache` write warning caused by the
consumer repository's Windows ACL.

Make pytest cache writes land in a writable project-local location, then rerun
the full suite without warnings. Keep test behavior, dependency versions, and
production deployment changes outside this unit.
