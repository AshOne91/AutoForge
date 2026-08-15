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
3. The operator starts or reconciles the named Compose project with
   `docker compose ... up -d --wait` after boot; this is the portable recovery
   command and is safe to repeat.
4. Automatic host bootstrap (systemd, Windows Task Scheduler, cloud-init, or
   AWS UserData) is a provider-specific adapter. The current supported selection
   is `tooling.single_host.bootstrap_provider: windows_task_scheduler`, which
   generates a repeatable PowerShell Compose-start script; registering the task
   remains an explicit host-operator action.

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
bootstrapping, backup/restore, retention, and operator recovery procedures remain
later operating work. AWS or another cloud provider is a later deployment target,
not an implicit dependency of this single-host baseline.
