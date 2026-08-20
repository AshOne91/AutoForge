# Next Task

## Next executable unit: add an opt-in KIS domestic balance integration check

Add one default-skipped KIS integration test for `KisDomesticAccountClient`. It
must require an explicit opt-in flag plus the existing KIS application and new
account runtime values, make exactly one read-only balance request, validate only
the typed holding contract, and close its HTTP/Redis resources.

Do not run the test without explicit configuration. Do not add a route,
persistence, account-summary output, Durable Job, polling, order behavior, or
credentials to Git.
