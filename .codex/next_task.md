# Next Task

## Next executable unit: hand the test-client fix to the KIS consumer

Regenerate KIS from its maintained specifications into a disposable workspace
and compare generator-owned output first. If the ownership manifest is clean,
apply only the AutoForge-owned test dependency update to the consumer and run
the KIS non-integration tests with warnings treated as errors. Preserve every
consumer-owned handler and do not start Docker profiles or trading-domain work.
