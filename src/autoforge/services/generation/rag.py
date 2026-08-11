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
        return f'''name: {specification.project.package_name}-rag

services:
  qdrant:
    profiles: ["rag"]
    image: qdrant/qdrant:v{rag.qdrant_version}
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{QDRANT_HTTP_PORT:-{base + 50}}}:6333"
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{QDRANT_GRPC_PORT:-{base + 51}}}:6334"
    volumes:
      - qdrant-storage:/qdrant/storage

  elasticsearch:
    profiles: ["rag"]
    image: docker.elastic.co/elasticsearch/elasticsearch:{rag.elasticsearch_version}
    environment:
      discovery.type: single-node
      xpack.security.enabled: "false"
      ES_JAVA_OPTS: -Xms512m -Xmx512m
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{ELASTICSEARCH_PORT:-{base + 60}}}:9200"
    volumes:
      - rag-elasticsearch-data:/usr/share/elasticsearch/data

  ollama:
    profiles: ["inference"]
    image: ollama/ollama:{rag.ollama_version}
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{OLLAMA_PORT:-{base + 70}}}:11434"
    volumes:
      - ollama-data:/root/.ollama

volumes:
  qdrant-storage:
  rag-elasticsearch-data:
  ollama-data:
'''

    @staticmethod
    def _render_env(specification: ProjectSpec) -> str:
        base = specification.tooling.rag.host_port_base
        return f'''# Copy to .env. This local profile contains no credentials.
LOCAL_BIND_ADDRESS=127.0.0.1
QDRANT_URL=http://qdrant:6333
QDRANT_HTTP_PORT={base + 50}
QDRANT_GRPC_PORT={base + 51}
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_PORT={base + 60}
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_PORT={base + 70}
'''

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        return f'''# Generated local RAG infrastructure

This optional overlay provides a local vector store (Qdrant), keyword search
(Elasticsearch), and local inference runtime (Ollama) for
`{specification.project.package_name}`. It does not create collections, indexes,
documents, embeddings, prompts, or models.

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

Qdrant and Elasticsearch use named Docker volumes because they own persistent
data. Ports bind to `LOCAL_BIND_ADDRESS` and default to the configured local
port block. `xpack.security.enabled` is disabled only for this local overlay.
Production requires authenticated, backed-up, cluster-aware service deployment;
do not use this Compose file as a production topology.
'''
