# Configuration and storage policy

This policy separates immutable generated code, environment configuration, and
runtime data. It is informed by the Base Server reference, where `APP_ENV`
selects an environment configuration, configuration is mounted read-only, and
file logs are mounted separately from the container lifecycle.

## Ownership and mount rules

| Category | Container path | Local Docker | Kubernetes |
| --- | --- | --- | --- |
| Generated code | `/app` | image only | image only |
| Non-secret environment config | `/app/config` | read-only bind mount | ConfigMap |
| Secrets | environment variables or secret file | ignored `.env` / secret store | Secret / workload identity |
| File logs | `/app/logs` | writable bind mount | PVC or log collector |
| Database, Redis, RabbitMQ data | service-owned path | named volume for local state | managed service or PVC |
| Build artifacts / uploads | service-specific path | named volume or explicit bind mount | object storage or PVC |

Do not mount a configuration directory over a generated source package. It can
hide image-owned code and make a generated image behave differently from the
same image in another environment.

## Environment selection

`APP_ENV` selects behavior such as `local`, `debug`, or `production`; it does
not select or contain credentials. A generated runtime should receive only the
configuration for its chosen environment, while secrets remain outside Git and
outside generated manifests.

## Generated boundary

Generated local environments mount `/app/logs` as writable runtime data. No
generator may emit an `/app/config:ro` mount unless the specification declares a
concrete non-secret configuration artifact. Generated configuration must preserve
user-owned files and must not mount over application source paths.

## Local service connectivity

`tooling.local_environment.database_provider` owns the local database runtime
selection. Its current supported value is `postgresql`. This is deliberately
separate from `ModuleSpec.database.provider: agnostic`, which describes portable
schema intent rather than a container image, DSN driver, or migration dialect.
A future MySQL provider must add its Compose, DSN, migration, and validation path
as one vertical slice before it becomes an accepted runtime value.
The approved first dialect is SQLAlchemy's async `mysql+asyncmy` connection form
with `utf8mb4`; its driver dependency belongs to the MySQL provider slice rather
than the default PostgreSQL installation.
In generated PostgreSQL HA mode, each Patroni node and each etcd member has its
own named volume. HAProxy has no persistent data. These local volumes are runtime
state: reset only an explicitly identified failed test node, never a whole Compose
project or unrelated service volumes as a recovery shortcut.

Generated Compose overlays remain independently managed. When an optional service
must communicate with the generated application or worker, the generator emits an
explicit non-secret network setting and attaches only the required services to the
same external named network. The current RAG overlay uses `RAG_NETWORK_NAME` for
this purpose; application and durable-job workers can resolve `qdrant`, `ollama`,
and the selected `elasticsearch` or `opensearch` service by DNS without relying on
host ports or Docker Desktop-specific host aliases. The external network is created
once by the operator and is not deleted by either Compose overlay.

## First operating target

The first operating target is a self-hosted single physical Docker host. The
generated services may still use replicas, Redis Cluster, PostgreSQL HA, durable
volumes, health checks, and restart policies so that service or container failures
are recoverable without a redesign. This is service-level HA, not protection from
loss of the physical host.

The single-host startup contract is deliberately platform-neutral:

1. Runtime services use `restart: unless-stopped` where they are expected to
   recover after a process or container failure.
2. The Docker daemon must be configured by the host operator to start during
   host boot.

This recovery boundary applies to the generated long-running services in the
optional RAG, MinIO storage, and ELK overlays. Their health checks gate readiness
where an image exposes a local health endpoint or native connectivity check;
one-shot initialization services remain `restart: "no"` and are rerun
idempotently when the overlay is started again.
All optional-service probes use the same 10-second interval, 5-second timeout,
and 30-retry budget; only the image-native probe command varies.
3. The operator starts or reconciles the named Compose project with
   `docker compose ... up -d --wait` after boot; this is the portable recovery
   command and is safe to repeat.
4. Automatic host bootstrap (systemd, Windows Task Scheduler, cloud-init, or
   AWS UserData) is a provider-specific adapter. The current supported selection
   is `tooling.single_host.bootstrap_provider: windows_task_scheduler`, which
   generates a repeatable PowerShell Compose-start script; registering the task
   remains an explicit host-operator action.

## Off-host backup boundary

The single-host profile stages two classes of backup artifacts outside the
project directory: verified PostgreSQL custom-format dumps and copied file-log
directories. AutoForge owns the artifact shape and checksum/restore evidence;
an operator or later deployment adapter owns transfer to off-host storage,
encryption keys, retention, and deletion policy. Restore validation must target
the same database image/extensions/roles or a disposable compatible target
before any live replacement is considered.

No cloud provider, upload schedule, or credential mechanism is implied by this
boundary. Those belong to a provider-specific backup adapter selected later.

The first adapter target is the S3-compatible object API. `StorageSpec` generates
the local MinIO overlay by default, while its Compose `storage` profile still
requires explicit operator selection to start. A project can set
`tooling.storage.enabled: false` to exclude generated object-storage artifacts.
The same profile includes an idempotent `minio-init` task that waits for MinIO
health and creates the generated `S3_BUCKET`. That task exits successfully after
initialization, so its overlay is started with `up -d`, not included in a Compose
`--wait` health gate. The same adapter boundary can later point at AWS S3 or
another compatible provider by changing endpoint, credentials, and lifecycle
policy outside generated code.

Infrastructure capabilities remain typed by responsibility rather than being
collapsed into one generic service list. Object storage owns bucket/object
contracts; a future MySQL capability will own database runtime, migration, and
connection contracts separately. This keeps provider-specific validation and
generation deterministic while allowing projects to select each capability.

### Adapter contract

The provider-neutral adapter receives an immutable artifact manifest containing
the artifact kind (`log` or `postgres_dump`), source-relative name, byte size,
creation time, and SHA-256 checksum. Its minimum responsibilities are:

1. stage or transfer the exact bytes to provider-owned storage;
2. return a durable object identifier and the recorded checksum;
3. verify a downloaded artifact before a restore attempt.

The adapter does not create database dumps, decide retention, or restore over a
live database. Those remain producer, policy-owner, and operator responsibilities
respectively. A failed transfer must leave the source artifact untouched and be
safe to retry with the same checksum.

The current in-memory manifest is `autoforge.core.backup.BackupArtifact`; it
normalizes workspace-relative names, UTC timestamps, non-negative byte sizes,
and lowercase SHA-256 values before any adapter receives it.
The transfer seam is `autoforge.core.backup.BackupTransfer`: providers implement
`put(artifact, source)` and `verify(object_id, expected_sha256)` without changing
the manifest or restore ownership contract.
Each adapter also exposes its validated `S3StorageConfig` through the
`configuration` property; the transfer seam does not resolve or persist secret
values.

The current provider-neutral configuration is
`autoforge.core.backup.S3StorageConfig`. It contains an HTTP(S) endpoint, bucket,
optional object-key prefix, and paired `SecretReference` values for access and
secret keys. It stores references only; resolving credentials, selecting an SDK,
and applying retention remain outside this core contract.
`S3StorageConfig.from_environment` is the generated-runtime handoff: it reads
the non-secret endpoint, bucket, and prefix values while retaining credential
variable names as `SecretReference` objects. `EnvironmentSecretProvider` then
resolves those references only when the selected infrastructure client opens.

The client boundary is intentionally injection-based: an infrastructure adapter
will provide an async S3-compatible client to the `BackupTransfer` implementation.
The core package does not select or import a concrete SDK, so the same contract
can use local MinIO, AWS S3, or another compatible endpoint.

`autoforge.infrastructure.backup.S3CompatibleBackupTransfer` is the reference
adapter. It validates the local manifest size, builds the configured object key,
and delegates byte transfer and remote checksum verification to the injected
client.

The selected concrete client library is `aioboto3`, exposed through the optional
`autoforge[backup]` extra. It remains outside the core package and is selected
because it provides async boto3-compatible S3 operations and custom endpoints;
the adapter still owns lifecycle management and credential resolution.

`autoforge.infrastructure.backup.Aioboto3S3Client` is the concrete wrapper. It
lazy-loads the optional dependency, manages the async client lifetime, resolves
runtime secret references, and records/verifies the manifest SHA-256 as object
metadata.

`autoforge backup` is the explicit preflight command for one already-created
artifact. It loads `S3_*` settings from the current process environment, uploads
the artifact, and verifies its remote checksum before reporting the object ID.
It does not create database dumps, schedule transfers, choose retention, or add
cloud credentials to generated application code.

The disposable integration check is `tests/integration/test_minio_backup.py`.
It runs only when the `backup` extra and the `AUTOFORGE_MINIO_ENDPOINT`,
`AUTOFORGE_MINIO_BUCKET`, `AUTOFORGE_MINIO_ACCESS_KEY`, and
`AUTOFORGE_MINIO_SECRET_KEY` environment variables are present.

The single-host startup contract is deliberately platform-neutral:

1. Runtime services use `restart: unless-stopped` where they are expected to
   recover after a process or container failure.
2. The Docker daemon must be configured by the host operator to start during
   host boot.
3. The operator starts or reconciles the named Compose project with
   `docker compose ... up -d --wait` after boot; this is the portable recovery
   command and is safe to repeat.
4. Automatic host bootstrap (systemd, Windows Task Scheduler, cloud-init, or
   AWS UserData) is a provider-specific adapter. The current supported selection
   is `tooling.single_host.bootstrap_provider: windows_task_scheduler`, which
   generates a repeatable PowerShell Compose-start script; registering the task
   remains an explicit host-operator action.

The disposable integration Compose profile remains a verification environment.
When explicitly selected, the generated single-host overlay composes with it to
add the public Nginx entry point, application replicas, and a configurable log
bind mount; it is not an implicit promotion of the integration profile. Host
bootstrapping and local backup/restore evidence are part of this baseline;
off-host transfer and retention remain provider-specific operating work. AWS or
another cloud provider is a later deployment target, not an implicit dependency
of this single-host baseline.
