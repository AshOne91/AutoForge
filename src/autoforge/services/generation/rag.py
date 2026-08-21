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

RAG_INFRASTRUCTURE_GENERATOR_ID = "autoforge.generator.rag_infrastructure"
RAG_INFRASTRUCTURE_GENERATOR_VERSION = "0.2.0"
NGINX_IMAGE = "nginx:1.27-alpine"


class RagInfrastructureGenerator:
    """Generate an opt-in local RAG infrastructure overlay."""

    @property
    def generator_id(self) -> str:
        return RAG_INFRASTRUCTURE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return RAG_INFRASTRUCTURE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        if not specification.tooling.rag.enabled:
            return {}
        rendered = {
            PurePosixPath("deploy", "rag", "compose.rag.yaml"): self._render_compose(
                specification
            ),
            PurePosixPath("deploy", "rag", ".env.example"): self._render_env(
                specification
            ),
            PurePosixPath("deploy", "rag", "README.md"): self._render_readme(
                specification
            ),
        }
        if specification.tooling.rag.search_mode == "cluster":
            rendered[PurePosixPath("deploy", "rag", "nginx", "search.conf")] = (
                self._render_search_proxy_config(specification)
            )
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
                    source="project:rag_infrastructure",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @classmethod
    def _render_compose(cls, specification: ProjectSpec) -> str:
        rag = specification.tooling.rag
        base = rag.host_port_base
        search_service = (
            cls._render_cluster_search_services(specification)
            if rag.search_mode == "cluster"
            else
            f'''  opensearch:
    profiles: ["rag"]
    image: opensearchproject/opensearch:{rag.opensearch_version}
    networks: [rag]
    environment:
      discovery.type: single-node
      DISABLE_INSTALL_DEMO_CONFIG: "true"
      DISABLE_SECURITY_PLUGIN: "true"
      OPENSEARCH_JAVA_OPTS: -Xms512m -Xmx512m
    restart: unless-stopped
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{OPENSEARCH_PORT:-{base + 60}}}:9200"
    volumes:
      - rag-opensearch-data:/usr/share/opensearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl --fail http://127.0.0.1:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30

'''
            if rag.search_backend == "opensearch"
            else f'''  elasticsearch:
    profiles: ["rag"]
    image: docker.elastic.co/elasticsearch/elasticsearch:{rag.elasticsearch_version}
    networks: [rag]
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    restart: unless-stopped
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{ELASTICSEARCH_PORT:-{base + 60}}}:9200"
    volumes:
      - rag-elasticsearch-data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl --fail http://127.0.0.1:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30

'''
        )
        search_volumes = (
            "\n".join(
                f"  rag-{rag.search_backend}-{index}-data:" for index in range(1, 4)
            )
            if rag.search_mode == "cluster"
            else f"  rag-{rag.search_backend}-data:"
        )
        return f'''name: {specification.project.package_name}-rag

services:
  qdrant:
    profiles: ["rag"]
    image: qdrant/qdrant:v{rag.qdrant_version}
    networks: [rag]
    restart: unless-stopped
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{QDRANT_HTTP_PORT:-{base + 50}}}:6333"
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{QDRANT_GRPC_PORT:-{base + 51}}}:6334"
    volumes:
      - qdrant-storage:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/127.0.0.1/6333'"]
      interval: 10s
      timeout: 5s
      retries: 30

{search_service}  ollama:
    profiles: ["inference"]
    image: ollama/ollama:{rag.ollama_version}
    networks: [rag]
    restart: unless-stopped
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{OLLAMA_PORT:-{base + 70}}}:11434"
    volumes:
      - ollama-data:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 30

networks:
  rag:
    name: ${{RAG_NETWORK_NAME:-{specification.project.package_name}-rag}}
    external: true

volumes:
  qdrant-storage:
{search_volumes}
  ollama-data:
'''

    @staticmethod
    def _render_cluster_search_services(specification: ProjectSpec) -> str:
        rag = specification.tooling.rag
        backend = rag.search_backend
        node_names = [f"{backend}-{index}" for index in range(1, 4)]
        nodes = ",".join(node_names)
        image = (
            f"opensearchproject/opensearch:{rag.opensearch_version}"
            if backend == "opensearch"
            else f"docker.elastic.co/elasticsearch/elasticsearch:{rag.elasticsearch_version}"
        )
        shared_environment = (
            f'''      cluster.name: ${{RAG_SEARCH_CLUSTER_NAME:-{specification.project.package_name}-rag-search}}
      discovery.seed_hosts: {nodes}
      cluster.initial_cluster_manager_nodes: {nodes}
      DISABLE_INSTALL_DEMO_CONFIG: "true"
      DISABLE_SECURITY_PLUGIN: "true"
      bootstrap.memory_lock: "true"
      OPENSEARCH_JAVA_OPTS: -Xms512m -Xmx512m
'''
            if backend == "opensearch"
            else f'''      cluster.name: ${{RAG_SEARCH_CLUSTER_NAME:-{specification.project.package_name}-rag-search}}
      discovery.seed_hosts: {nodes}
      cluster.initial_master_nodes: {nodes}
      xpack.security.enabled: "false"
      ES_JAVA_OPTS: -Xms512m -Xmx512m
'''
        )
        ulimits = (
            '''    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
'''
            if backend == "opensearch"
            else ""
        )
        node_services = "\n".join(
            f'''  {node_name}:
    profiles: ["rag"]
    image: {image}
    networks: [rag]
    restart: unless-stopped
    environment:
      node.name: {node_name}
{shared_environment}{ulimits}    volumes:
      - rag-{backend}-{index}-data:/usr/share/{backend}/data
    healthcheck:
      test: ["CMD-SHELL", 'curl --fail "http://127.0.0.1:9200/_cluster/health?wait_for_nodes=3&timeout=1s" || exit 1']
      interval: 10s
      timeout: 5s
      retries: 30
'''
            for index, node_name in enumerate(node_names, start=1)
        )
        dependencies = "\n".join(
            f'''      {node_name}:
        condition: service_healthy'''
            for node_name in node_names
        )
        return f'''  search:
    profiles: ["rag"]
    image: {NGINX_IMAGE}
    networks: [rag]
    restart: unless-stopped
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RAG_SEARCH_PORT:-{rag.host_port_base + 60}}}:9200"
    volumes:
      - ./nginx/search.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
{dependencies}
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O - http://127.0.0.1:9200/_cluster/health >/dev/null || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30

{node_services}
'''

    @staticmethod
    def _render_search_proxy_config(specification: ProjectSpec) -> str:
        backend = specification.tooling.rag.search_backend
        nodes = "\n".join(
            f"    server {backend}-{index}:9200 max_fails=1 fail_timeout=2s;"
            for index in range(1, 4)
        )
        return f'''upstream search_backend {{
    least_conn;
{nodes}
}}

server {{
    listen 9200;
    client_max_body_size 0;

    location / {{
        proxy_pass http://search_backend;
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
    def _render_env(specification: ProjectSpec) -> str:
        rag = specification.tooling.rag
        base = rag.host_port_base
        search_name = rag.search_backend
        search_endpoint = "search" if rag.search_mode == "cluster" else search_name
        search_port_name = (
            "RAG_SEARCH_PORT"
            if rag.search_mode == "cluster"
            else f"{search_name.upper()}_PORT"
        )
        return f'''# Copy to .env. This local profile contains no credentials.
LOCAL_BIND_ADDRESS=127.0.0.1
RAG_NETWORK_NAME={specification.project.package_name}-rag
QDRANT_URL=http://qdrant:6333
QDRANT_HTTP_PORT={base + 50}
QDRANT_GRPC_PORT={base + 51}
RAG_SEARCH_BACKEND={search_name}
RAG_SEARCH_URL=http://{search_endpoint}:9200
{search_name.upper()}_URL=http://{search_endpoint}:9200
{search_port_name}={base + 60}
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_PORT={base + 70}
'''

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        search_name = specification.tooling.rag.search_backend.title()
        topology_note = (
            "\nThe `cluster` search mode creates three search members behind the "
            "generated `search:9200` endpoint. Consumers continue to use "
            "`RAG_SEARCH_URL`; the proxy retries another healthy member when one "
            "node stops. This is one-host logical-node recovery, not host-level HA.\n"
            if specification.tooling.rag.search_mode == "cluster"
            else ""
        )
        return f'''# Generated local RAG infrastructure

This optional overlay provides a local vector store (Qdrant), keyword search
({search_name}), and local inference runtime (Ollama) for
`{specification.project.package_name}`. It does not create collections, indexes,
documents, embeddings, prompts, or models.

Create the shared network once before starting either the RAG overlay or the
generated local environment. It lets separately managed Compose projects use
service DNS without exposing internal container ports through the host.

```powershell
if (-not (docker network inspect {specification.project.package_name}-rag 2>$null)) {{
  docker network create {specification.project.package_name}-rag
}}
```

```powershell
Copy-Item deploy/rag/.env.example deploy/rag/.env
docker compose --env-file deploy/rag/.env -f deploy/rag/compose.rag.yaml --profile rag up -d
docker compose --env-file deploy/rag/.env -f deploy/rag/compose.rag.yaml --profile rag down
```

Start Ollama only when local inference is needed. The image and every model use
substantial disk space, so no model is downloaded automatically.

```powershell
docker compose --env-file deploy/rag/.env -f deploy/rag/compose.rag.yaml --profile inference up -d
docker compose --env-file deploy/rag/.env -f deploy/rag/compose.rag.yaml exec ollama ollama pull <selected-model>
```

Qdrant and {search_name} use named Docker volumes because they own persistent
data. Ports bind to `LOCAL_BIND_ADDRESS` and default to the configured local
port block. Search-engine security is disabled only for this local overlay.
{topology_note}
Production requires authenticated, backed-up, cluster-aware service deployment;
do not use this Compose file as a production topology.
'''
