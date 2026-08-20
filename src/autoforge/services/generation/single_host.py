from pathlib import PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import ProjectSpec

SINGLE_HOST_GENERATOR_ID = "autoforge.generator.single-host"
SINGLE_HOST_GENERATOR_VERSION = "0.1.0"


class SingleHostOperatingGenerator:
    """Generate the public proxy overlay for a local Docker service environment."""

    @property
    def generator_id(self) -> str:
        return SINGLE_HOST_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return SINGLE_HOST_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        profile = specification.tooling.single_host
        if not profile.enabled:
            return {}

        files = {
            PurePosixPath("deploy", "single-host", "compose.override.yml"): self._render_compose(
                application_replicas=profile.application_replicas,
                public_port=specification.tooling.local_environment.host_port_base or 28000,
            ),
            PurePosixPath("deploy", "single-host", "runtime.env.example"): self._render_environment(
                public_port=specification.tooling.local_environment.host_port_base or 28000
            ),
            PurePosixPath("deploy", "single-host", "nginx", "default.conf.template"): self._render_nginx(),
            PurePosixPath("deploy", "single-host", "README.md"): self._render_readme(
                specification,
                application_replicas=profile.application_replicas,
            ),
        }
        if profile.bootstrap_provider == "windows_task_scheduler":
            files[PurePosixPath("deploy", "single-host", "windows", "start-compose.ps1")] = (
                self._render_windows_bootstrap()
            )
        return files

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        rendered = self.render(specification)
        spec_hash = specification_hash(specification)
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=[
                PlannedFile(
                    relative_path=path,
                    generator_id=self.generator_id,
                    generator_version=self.generator_version,
                    ownership=FileOwnership.GENERATED,
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:single-host",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _render_compose(*, application_replicas: int, public_port: int) -> str:
        return f"""services:
  application:
    deploy:
      replicas: {application_replicas}
    ports: !reset []
    volumes:
      - ${{LOG_ROOT:-../logs}}:/app/logs

  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    environment:
      UPSTREAM_HOST: application
      NGINX_ENVSUBST_FILTER: UPSTREAM_HOST
    ports:
      - "${{PUBLIC_BIND_ADDRESS:-0.0.0.0}}:${{PUBLIC_HTTP_PORT:-{public_port}}}:80"
    volumes:
      - ../deploy/single-host/nginx/default.conf.template:/etc/nginx/templates/default.conf.template:ro
    depends_on:
      application:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20
"""

    @staticmethod
    def _render_environment(*, public_port: int) -> str:
        return f"""# Compose runtime settings for the single-host public proxy.\nPUBLIC_BIND_ADDRESS=0.0.0.0\nPUBLIC_HTTP_PORT={public_port}\nLOG_ROOT=../logs\n"""

    @staticmethod
    def _render_windows_bootstrap() -> str:
        return r'''$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $ProjectRoot

$deadline = (Get-Date).AddMinutes(5)
do {
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)
if ($LASTEXITCODE -ne 0) { throw "Docker engine did not become ready within 5 minutes." }

$composeArgs = @(
  "--env-file", "environment\.env",
  "--env-file", "deploy\single-host\runtime.env",
  "-f", "environment\compose.integration.yml",
  "-f", "deploy\single-host\compose.override.yml"
)
$composeConfig = docker compose @composeArgs config --format json
if ($LASTEXITCODE -ne 0) { throw "Docker Compose configuration is invalid." }
$config = $composeConfig | ConvertFrom-Json
$ragNetworkDefinition = $config.networks.PSObject.Properties | Where-Object { $_.Name -eq "rag" } | Select-Object -First 1
if ($null -ne $ragNetworkDefinition -and $ragNetworkDefinition.Value.external) {
  $ragNetworkName = [string]$ragNetworkDefinition.Value.name
  docker network inspect $ragNetworkName *> $null
  if ($LASTEXITCODE -ne 0) {
    throw "External RAG network '$ragNetworkName' is missing. Start the generated RAG overlay first."
  }
}
$published = @{}
foreach ($service in $config.services.PSObject.Properties) {
  foreach ($port in @($service.Value.ports)) {
    if ($null -eq $port.published) { continue }
    $publishedPort = [int]$port.published
    if ($published.ContainsKey($publishedPort)) {
      throw "Published host port collision: $publishedPort ($($published[$publishedPort]) and $($service.Name))"
    }
    $published[$publishedPort] = $service.Name
  }
}

$env:COMPOSE_IGNORE_ORPHANS = "true"
docker compose @composeArgs build
if ($LASTEXITCODE -ne 0) { throw "Docker Compose image build failed." }
if ($null -ne $ragNetworkDefinition -and $ragNetworkDefinition.Value.external) {
  $ragPreflight = @'
from urllib.request import urlopen
import os
urlopen(os.environ["RAG_SEARCH_URL"] + "/_cluster/health", timeout=5).read()
urlopen(os.environ["RAG_OLLAMA_URL"] + "/api/tags", timeout=5).read()
'@
  $ragPreflight | docker compose @composeArgs run --rm --no-deps --no-TTY --entrypoint python application -
  if ($LASTEXITCODE -ne 0) {
    throw "RAG endpoints are unavailable. Start the generated RAG overlay and inference profile first."
  }
}
docker compose @composeArgs up -d --wait
'''

    @staticmethod
    def _render_nginx() -> str:
        return """resolver 127.0.0.11 ipv6=off valid=10s;

map $http_upgrade $connection_upgrade {
  default upgrade;
  '' close;
}

server {
  listen 80;

  location / {
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Instance-Name $hostname;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    set $upstream ${UPSTREAM_HOST}:8000;
    proxy_pass http://$upstream;
  }
}
"""

    @staticmethod
    def _render_readme(
        specification: ProjectSpec, *, application_replicas: int
    ) -> str:
        host_port_base = specification.tooling.local_environment.host_port_base
        bootstrap_note = (
            "A Windows Task Scheduler adapter is generated at "
            "`deploy/single-host/windows/start-compose.ps1`; register it to run "
            "after Docker Desktop starts.\n"
            if specification.tooling.single_host.bootstrap_provider == "windows_task_scheduler"
            else ""
        )
        rag_note = (
            "RAG is selected for this project. Start the separately managed "
            "`deploy/rag/compose.rag.yaml` overlay (including the `inference` "
            "profile when indexing is enabled) before this Compose overlay. The "
            "Windows bootstrap checks the configured search and Ollama endpoints "
            "before starting the application.\n"
            if specification.tooling.rag.enabled
            else ""
        )
        port_block = (
            f"""
## Generated host-port block

This project uses the AutoForge-generated local block beginning at `{host_port_base}`:

| Service | Host port |
| --- | ---: |
| public application proxy | `{host_port_base}` |
| PostgreSQL/HAProxy | `{host_port_base + 10}` |
| RabbitMQ AMQP | `{host_port_base + 30}` |
| RabbitMQ management | `{host_port_base + 31}` |
| Airflow | `{host_port_base + 40}` |

The application, database, broker, and scheduler communicate through Compose
service names and container ports. Do not assign another generated environment
the same block. The authoritative allocation rules live in [AutoForge's local
Docker port policy](https://github.com/AshOne91/AutoForge/blob/main/docs/architecture/local_port_policy.md).
Individual environment variables are one-off deployment overrides; changing them
does not make `ProjectSpec` revalidate a runtime collision.
"""
            if host_port_base is not None
            else ""
        )
        return (
            f"""# Generated single-host operating overlay

This generated overlay keeps `environment/compose.integration.yml` as the
dependency runtime and adds one public Nginx entry point with
`application` scaled to {application_replicas} replicas. It is service-level HA on
one Docker host: it recovers containers, not loss of the physical machine.

```powershell
Copy-Item environment/.env.example environment/.env
Copy-Item deploy/single-host/runtime.env.example deploy/single-host/runtime.env
# Replace every sample credential in environment/.env before starting.
docker compose --env-file environment/.env --env-file deploy/single-host/runtime.env -f environment/compose.integration.yml -f deploy/single-host/compose.override.yml build
docker compose --env-file environment/.env --env-file deploy/single-host/runtime.env -f environment/compose.integration.yml -f deploy/single-host/compose.override.yml up -d --wait
docker compose --env-file environment/.env --env-file deploy/single-host/runtime.env -f environment/compose.integration.yml -f deploy/single-host/compose.override.yml down
```

Before `up`, validate every environment file that publishes host ports:

```powershell
python -m autoforge.main validate-ports --env-file environment/.env --env-file deploy/single-host/runtime.env
```

The check is read-only and rejects duplicate published host ports; it does not
allocate ports or replace specification validation.

{rag_note}{bootstrap_note}The Windows bootstrap performs the same read-only Compose port-collision
preflight, then builds the local application image before starting containers. The public proxy listens on
`PUBLIC_BIND_ADDRESS:PUBLIC_HTTP_PORT`; application,
database, Redis, RabbitMQ, and Airflow host ports remain governed by the integration
environment. `LOG_ROOT` is a host bind mount so file logs survive application
container recreation. Keep `environment/.env` outside Git. Configure host firewall,
TLS termination, off-host backup, and Docker service auto-start before exposing the
host to an untrusted network.
{port_block}
""".strip()
            + "\n"
        )
