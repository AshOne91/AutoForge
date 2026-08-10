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
        version = specification.tooling.elk.version
        return f"""name: {specification.project.package_name}-observability

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:{version}
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
      xpack.license.self_generated.type: basic
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    ports:
      - "127.0.0.1:${{ELASTICSEARCH_PORT:-9200}}:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:{version}
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
      XPACK_SECURITY_ENABLED: "false"
    ports:
      - "127.0.0.1:${{KIBANA_PORT:-5601}}:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:{version}
    user: root
    command: ["filebeat", "-e", "--strict.perms=false", "-c", "/usr/share/filebeat/filebeat.yml"]
    volumes:
      - ${{LOG_ROOT:-./logs}}:/var/log/application:ro
      - ${{FILEBEAT_CONFIG:-./deploy/observability/filebeat.yml}}:/usr/share/filebeat/filebeat.yml:ro
    depends_on:
      - elasticsearch

volumes:
  elasticsearch-data:
"""

    @staticmethod
    def _render_filebeat(specification: ProjectSpec) -> str:
        package_name = specification.project.package_name
        return f"""filebeat.inputs:
  - type: filestream
    id: {package_name}-application-json
    enabled: true
    paths:
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
  hosts: ["http://elasticsearch:9200"]
"""

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        return f"""# Generated ELK development profile

This profile collects JSON-lines application logs for `{specification.project.package_name}`:

- Filebeat reads `LOG_ROOT/*/*.log` as NDJSON.
- Elasticsearch stores the indexed logs in the `elasticsearch-data` volume.
- Kibana is available at `http://127.0.0.1:$KIBANA_PORT` (default `5601`).

Start it together with the application's integration Compose file:

```powershell
docker compose -f <base-compose-file> -f deploy/observability/compose.elk.yaml up -d
```

Set `LOG_ROOT` when logs are stored outside `./logs`. Set `ELASTICSEARCH_PORT`,
`KIBANA_PORT`, or `FILEBEAT_CONFIG` when the defaults conflict with the host.

This is a local development profile. Security is disabled and the ports bind to
localhost. Production requires authenticated Elasticsearch/Kibana and a
cluster-aware collector such as a Filebeat or Fluent Bit DaemonSet; do not use
this overlay as a production deployment.
"""
