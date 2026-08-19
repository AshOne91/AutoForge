# Next Task

## Next executable unit: KIS operator endpoint live verification

The generated operator-only human endpoint is implemented and covered by the
full KIS test suite. The next bounded unit is a disposable live Compose check
that exercises login, operator provisioning, session revocation, and the
read-only `/api/identity/operator/session` request through the generated
runtime. It must reuse the existing Identity, Redis, and access-level contracts;
do not add new persistence or authorization rules.
