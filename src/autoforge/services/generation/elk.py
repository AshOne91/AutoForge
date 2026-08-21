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
ELK_GENERATOR_VERSION = "0.2.0"
NGINX_IMAGE = "nginx:1.27-alpine"


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
        rendered = {
            PurePosixPath("deploy", "observability", "compose.elk.yaml"):
                self._render_compose(specification),
            PurePosixPath("deploy", "observability", "filebeat.yml"):
                self._render_filebeat(specification),
            PurePosixPath("deploy", "observability", "README.md"):
                self._render_readme(specification),
        }
        if (
            specification.tooling.elk.mode == "central"
            and specification.tooling.elk.elasticsearch_mode == "cluster"
        ):
            rendered[PurePosixPath("deploy", "observability", "nginx", "elasticsearch.conf")] = self._render_elasticsearch_proxy_config()
        return rendered

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
        if specification.tooling.elk.elasticsearch_mode == "cluster":
            return ElkStackGenerator._render_cluster_compose(specification)
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
    def _render_cluster_compose(specification: ProjectSpec) -> str:
        version = specification.tooling.elk.version
        base = specification.tooling.elk.host_port_base
        node_names = [f"elasticsearch-{index}" for index in range(1, 4)]
        nodes = ",".join(node_names)
        dependencies = "\n".join(
            f'''      {node_name}:
        condition: service_healthy'''
            for node_name in node_names
        )
        node_services = "\n".join(
            f'''  {node_name}:
    image: docker.elastic.co/elasticsearch/elasticsearch:{version}
    environment:
      node.name: {node_name}
      cluster.name: ${{ELK_CLUSTER_NAME:-{specification.project.package_name}-elk}}
      discovery.seed_hosts: {nodes}
      cluster.initial_master_nodes: {nodes}
      xpack.security.enabled: "false"
      xpack.license.self_generated.type: basic
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    restart: unless-stopped
    volumes:
      - elasticsearch-{index}-data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", 'curl --fail "http://127.0.0.1:9200/_cluster/health?wait_for_nodes=3&timeout=1s" || exit 1']
      interval: 10s
      timeout: 5s
      retries: 30
'''
            for index, node_name in enumerate(node_names, start=1)
        )
        return f'''services:
  elasticsearch:
    image: {NGINX_IMAGE}
    restart: unless-stopped
    ports:
      - "127.0.0.1:${{ELASTICSEARCH_PORT:-{base}}}:9200"
    volumes:
      - ./nginx/elasticsearch.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
{dependencies}
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O - http://127.0.0.1:9200/_cluster/health >/dev/null || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30

{node_services}
  kibana:
    image: docker.elastic.co/kibana/kibana:{version}
    restart: unless-stopped
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
      XPACK_SECURITY_ENABLED: "false"
    ports:
      - "127.0.0.1:${{KIBANA_PORT:-{base + 1}}}:5601"
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
  elasticsearch-1-data:
  elasticsearch-2-data:
  elasticsearch-3-data:
  filebeat-data:
'''

    @staticmethod
    def _render_elasticsearch_proxy_config() -> str:
        nodes = "\n".join(
            f"    server elasticsearch-{index}:9200 max_fails=1 fail_timeout=2s;"
            for index in range(1, 4)
        )
        return f'''upstream elasticsearch_backend {{
    least_conn;
{nodes}
}}

server {{
    listen 9200;
    client_max_body_size 0;

    location / {{
        proxy_pass http://elasticsearch_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 3;
    }}
}}
'''

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
      - ${{LOG_ROOT:-../../logs}}:/var/log/application:ro
      - ${{FILEBEAT_CONFIG:-../../deploy/observability/filebeat.yml}}:/usr/share/filebeat/filebeat.yml:ro
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
        elk = specification.tooling.elk
        mode = elk.mode
        host_port_base = elk.host_port_base
        if mode == "collector":
            startup = (
                "$env:ELASTICSEARCH_HOST = \"http://central-elasticsearch:9200\"\n"
                "docker compose -f deploy/observability/compose.elk.yaml up -d"
            )
            description = "This collector-only profile runs Filebeat on one application host."
            storage = "- Filebeat forwards logs to the configured central Elasticsearch host."
        else:
            startup = (
                "docker compose -f <base-compose-file> -f "
                "deploy/observability/compose.elk.yaml up -d"
            )
            if elk.elasticsearch_mode == "cluster":
                description = (
                    "This profile runs three Elasticsearch members behind one stable "
                    "proxy, with Kibana and Filebeat."
                )
                storage = (
                    "- Each Elasticsearch member stores indexed logs in its own named volume.\n"
                    "- Filebeat and Kibana keep the stable `elasticsearch:9200` address; "
                    "they do not address a member directly."
                )
            else:
                description = "This profile runs a local Elasticsearch, Kibana and Filebeat stack."
                storage = "- Elasticsearch stores indexed logs in the `elasticsearch-data` volume."
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

Set `LOG_ROOT` when logs are stored outside the default path. Central mode uses
`../logs` with the generated integration Compose file; collector mode uses
`../../logs` when its overlay is run standalone. Set `ELASTICSEARCH_PORT`,
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
