# Next Task

## Next executable unit: run one explicit live read-only KIS price check

After the operator configures `KIS_API_URL`, `KIS_APP_KEY`, and
`KIS_APP_SECRET`, explicitly enable the existing current-price integration
check. It performs exactly one read-only domestic-price GET (default stock code
`005930`), prints no secrets, and closes its HTTP and Redis clients. Do not run
the balance check, submit an order, add polling, or create trading policy. Fix
AutoForge only if this consumer proof reveals a generated-contract defect.
