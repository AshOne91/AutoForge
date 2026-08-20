# Next Task

## Next executable unit: implement one read-only KIS domestic balance client

Add user-owned `KisDomesticAccountClient` on the existing generated
`ExternalProvider` and Redis-backed `KisTokenCoordinator` contracts. It calls
only `GET /uapi/domestic-stock/v1/trading/inquire-balance`, selects the official
real/demo TR ID, follows at most ten continuation pages, and returns only typed
holding fields needed for later portfolio composition.

Declare the KIS account-number, account-product-code, and real/demo environment
as application-only runtime environments. Use deterministic fake transport tests
for request shape, pagination, malformed/error responses, and pre-I/O input
validation. Do not add an HTTP route, persistence, account-summary exposure,
live KIS request, portfolio write, or order behavior.
