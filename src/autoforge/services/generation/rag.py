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
RAG_INFRASTRUCTURE_GENERATOR_VERSION = "0.1.0"


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
        return {
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

    @staticmethod
    def _render_compose(specification: ProjectSpec) -> str:
        rag = specification.tooling.rag
        base = rag.host_port_base
        search_service = (
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
        search_volume = f"rag-{rag.search_backend}-data"
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
  {search_volume}:
  ollama-data:
'''

    @staticmethod
    def _render_env(specification: ProjectSpec) -> str:
        rag = specification.tooling.rag
        base = rag.host_port_base
        search_name = rag.search_backend
        search_port_name = f"{search_name.upper()}_PORT"
        return f'''# Copy to .env. This local profile contains no credentials.
LOCAL_BIND_ADDRESS=127.0.0.1
RAG_NETWORK_NAME={specification.project.package_name}-rag
QDRANT_URL=http://qdrant:6333
QDRANT_HTTP_PORT={base + 50}
QDRANT_GRPC_PORT={base + 51}
RAG_SEARCH_BACKEND={search_name}
RAG_SEARCH_URL=http://{search_name}:9200
{search_name.upper()}_URL=http://{search_name}:9200
{search_port_name}={base + 60}
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_PORT={base + 70}
'''

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        search_name = specification.tooling.rag.search_backend.title()
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
Production requires authenticated, backed-up, cluster-aware service deployment;
do not use this Compose file as a production topology.
'''
