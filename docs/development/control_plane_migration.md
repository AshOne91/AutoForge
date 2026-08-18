# Control Plane Provider Migration

This is an operator procedure for the migration boundary defined in the
[Control Plane persistence architecture](../architecture/control_plane_persistence.md).
It does not replace that architecture contract.

Install the optional server dependencies, then provide the PostgreSQL URL only
through the deployment environment or secret provider.

```powershell
python -m pip install -e ".[server]"
$env:AUTOFORGE_DATABASE_URL = "postgresql+asyncpg://..."
python -m autoforge.main migrate-control-plane `
  --migration-directory deploy/postgresql/init
```

The command prints only newly applied numeric migration versions, one per line.
No output with exit code `0` means the ledger already matches the supplied SQL
artifacts. A nonzero exit code means the provider must stop application rollout
and inspect the provider-side error before retrying.

Run this command explicitly as a provider deployment step before Control Plane
application rollout. Do not invoke it from FastAPI startup, the generated
Kubernetes runtime manifest, or a generated Kubernetes Job.

## Control Plane container image

`deploy/control-plane/Dockerfile` packages the declared SQL artifacts and keeps
`migrate-control-plane` available as an explicit image command. Its default
command still starts the Control Plane server.

```powershell
docker run --rm --network <provider-network> `
  --env AUTOFORGE_DATABASE_URL="postgresql+asyncpg://..." `
  autoforge-control-plane:<tag> migrate-control-plane
```

The local Control Plane Compose profile uses this same explicit path. Its
one-shot `control-plane-migrate` service waits for PostgreSQL, applies and
records the artifacts, and the long-running `control-plane` service waits for
that successful completion. PostgreSQL no longer receives the SQL directory
through `docker-entrypoint-initdb.d`.

Volumes created by the known earlier Compose profile may contain schema SQL
without migration-ledger evidence. The current provider CLI reconciles that
exact published artifact set in one transaction: the idempotent SQL remains
unchanged, `007` seeds versions `1` through `6` with their checksums, and the
executor records version `7`. Back up and separately review a volume with
manual schema changes before using this path.
