# Next Task

## Next executable unit: expose operator-only domestic holdings

Register the user-owned `KisDomesticAccountClient` through the existing
application lifespan and add one internal operator-token-protected GET that
returns its typed domestic holding list. Reuse the existing `operator` service
token, safe failure mapping, and fake FastAPI test pattern.

Do not create a public route, persist portfolio data, return `output2` account
summaries, add polling/Durable Jobs, expose an order action, or run a live KIS
request. Keep the application-owned client closed during lifespan shutdown.
