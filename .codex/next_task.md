# Next Task

## Next executable unit: single-host bootstrap composition contract

Inspect the generated Windows `start-compose.ps1` path and its owning
`SingleHostOperatingGenerator` test. Confirm that a selected `single_host`
profile starts the dependency base Compose and the generated overlay together,
so the documented Nginx and configured application scale actually apply after
host boot. Add a focused generator test only if that composition contract is
not already covered.

Keep the base integration Compose separately runnable for resource-light
development. Do not change active local Docker projects or add another
bootstrap provider.
