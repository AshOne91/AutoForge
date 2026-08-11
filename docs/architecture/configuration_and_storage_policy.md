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
