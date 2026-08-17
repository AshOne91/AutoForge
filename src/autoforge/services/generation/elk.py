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

ELK_GENERATOR_ID = "autoforge.generator.elk"
ELK_GENERATOR_VERSION = "0.1.0"


class ElkStackGenerator:
    """Generate a disposable ELK overlay for the application's JSON log files."""

    @property
    def generator_id(self) -> str:
        return ELK_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return ELK_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        if not specification.tooling.elk.enabled:
            return {}
        return {
            PurePosixPath("deploy", "observability", "compose.elk.yaml"):
                self._render_compose(specification),
            PurePosixPath("deploy", "observability", "filebeat.yml"):
                self._render_filebeat(specification),
            PurePosixPath("deploy", "observability", "README.md"):
                self._render_readme(specification),
        }

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
                    source="project:elk",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_compose(specification: ProjectSpec) -> str:
        if specification.tooling.elk.mode == "collector":
            return ElkStackGenerator._render_collector_compose(specification)
        version = specification.tooling.elk.version
        host_port_base = specification.tooling.elk.host_port_base
        return f"""services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:{version}
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
      xpack.license.self_generated.type: basic
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    restart: unless-stopped
    ports:
      - "127.0.0.1:${{ELASTICSEARCH_PORT:-{host_port_base}}}:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl --fail http://127.0.0.1:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30

  kibana:
    image: docker.elastic.co/kibana/kibana:{version}
    restart: unless-stopped
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
      XPACK_SECURITY_ENABLED: "false"
    ports:
      - "127.0.0.1:${{KIBANA_PORT:-{host_port_base + 1}}}:5601"
    depends_on:
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl --fail http://127.0.0.1:5601/api/status || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30

  filebeat:
    image: docker.elastic.co/beats/filebeat:{version}
    user: root
    command: ["filebeat", "-e", "--strict.perms=false", "-c", "/usr/share/filebeat/filebeat.yml"]
    restart: unless-stopped
    volumes:
      - ${{LOG_ROOT:-../logs}}:/var/log/application:ro
      - ${{FILEBEAT_CONFIG:-../deploy/observability/filebeat.yml}}:/usr/share/filebeat/filebeat.yml:ro
      - filebeat-data:/usr/share/filebeat/data
    depends_on:
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "filebeat", "test", "config", "-e", "--strict.perms=false", "-c", "/usr/share/filebeat/filebeat.yml"]
      interval: 10s
      timeout: 5s
      retries: 30

volumes:
  elasticsearch-data:
  filebeat-data:
"""

    @staticmethod
    def _render_collector_compose(specification: ProjectSpec) -> str:
        version = specification.tooling.elk.version
        return f"""services:
  filebeat:
    image: docker.elastic.co/beats/filebeat:{version}
    user: root
    environment:
      ELASTICSEARCH_HOST: ${{ELASTICSEARCH_HOST:?Set ELASTICSEARCH_HOST}}
    command: ["filebeat", "-e", "--strict.perms=false", "-c", "/usr/share/filebeat/filebeat.yml"]
    restart: unless-stopped
    volumes:
      - ${{LOG_ROOT:-../logs}}:/var/log/application:ro
      - ${{FILEBEAT_CONFIG:-../deploy/observability/filebeat.yml}}:/usr/share/filebeat/filebeat.yml:ro
      - filebeat-data:/usr/share/filebeat/data
    healthcheck:
      test: ["CMD", "filebeat", "test", "config", "-e", "--strict.perms=false", "-c", "/usr/share/filebeat/filebeat.yml"]
      interval: 10s
      timeout: 5s
      retries: 30

volumes:
  filebeat-data:
"""

    @staticmethod
    def _render_filebeat(specification: ProjectSpec) -> str:
        package_name = specification.project.package_name
        elasticsearch_host = (
            "http://elasticsearch:9200"
            if specification.tooling.elk.mode == "central"
            else "${ELASTICSEARCH_HOST}"
        )
        return f"""filebeat.inputs:
  - type: filestream
    id: {package_name}-application-json
    enabled: true
    paths:
      - /var/log/application/*.log
      - /var/log/application/*/*.log
    parsers:
      - ndjson:
          target: ""
          add_error_key: true

fields_under_root: true
fields:
  autoforge.project: {package_name}
  autoforge.environment: development

output.elasticsearch:
  hosts: ["{elasticsearch_host}"]
"""

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        mode = specification.tooling.elk.mode
        host_port_base = specification.tooling.elk.host_port_base
        if mode == "collector":
            startup = (
                "$env:ELASTICSEARCH_HOST = \"http://central-elasticsearch:9200\"\n"
                "docker compose -f deploy/observability/compose.elk.yaml up -d"
            )
            description = "This collector-only profile runs Filebeat on one application host."
        else:
            startup = (
                "docker compose -f <base-compose-file> -f "
                "deploy/observability/compose.elk.yaml up -d"
            )
            description = "This profile runs a local Elasticsearch, Kibana and Filebeat stack."
        storage = (
            "- Elasticsearch stores indexed logs in the `elasticsearch-data` volume."
            if mode == "central"
            else "- Filebeat forwards logs to the configured central Elasticsearch host."
        )
        access = (
            f"- Kibana is available at `http://127.0.0.1:$KIBANA_PORT` (default `{host_port_base + 1}`)."
            if mode == "central"
            else "- This profile does not expose Elasticsearch or Kibana ports."
        )
        return f"""# Generated ELK development profile

{description} It collects JSON-lines application logs for `{specification.project.package_name}`:

- Filebeat reads `LOG_ROOT/*.log` and `LOG_ROOT/*/*.log` as NDJSON.
- Filebeat preserves its read registry in the `filebeat-data` volume.
{storage}
{access}

Start it together with the application's integration Compose file:

```powershell
{startup}
```

Set `LOG_ROOT` when logs are stored outside the default `../logs` path used with
the generated integration Compose file. Set `ELASTICSEARCH_PORT`,
`KIBANA_PORT`, or `FILEBEAT_CONFIG` when the defaults conflict with the host.

To find exhausted durable-job retries in the central profile, query the
structured event field:

```powershell
$query = '{{"query":{{"term":{{"event_type":"news_collection_retries_exhausted"}}}}}}'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:{host_port_base}/filebeat-*/_search' `
  -ContentType 'application/json' -Body $query
```

This is a local development profile. The central mode disables security and
binds its ports to localhost. Production requires authenticated
Elasticsearch/Kibana and a cluster-aware collector such as a Filebeat or Fluent
Bit DaemonSet; do not use this overlay as a production deployment.
"""
