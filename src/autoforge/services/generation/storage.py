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

OBJECT_STORAGE_GENERATOR_ID = "autoforge.generator.storage"
OBJECT_STORAGE_GENERATOR_VERSION = "0.1.0"
MINIO_IMAGE = "minio/minio:RELEASE.2025-07-23T15-54-02Z"


class ObjectStorageGenerator:
    """Generate an opt-in local S3-compatible object storage overlay."""

    @property
    def generator_id(self) -> str:
        return OBJECT_STORAGE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return OBJECT_STORAGE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        if not specification.tooling.storage.enabled:
            return {}
        return {
            PurePosixPath("deploy", "storage", "compose.storage.yaml"): self._render_compose(
                specification
            ),
            PurePosixPath("deploy", "storage", ".env.example"): self._render_env(
                specification
            ),
            PurePosixPath("deploy", "storage", "README.md"): self._render_readme(
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
                    source="project:object_storage",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_compose(specification: ProjectSpec) -> str:
        base = specification.tooling.storage.host_port_base
        return f'''name: {specification.project.package_name}-storage

services:
  minio:
    profiles: ["storage"]
    image: {MINIO_IMAGE}
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${{MINIO_ROOT_USER:?set MINIO_ROOT_USER}}
      MINIO_ROOT_PASSWORD: ${{MINIO_ROOT_PASSWORD:?set MINIO_ROOT_PASSWORD}}
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{MINIO_API_PORT:-{base + 80}}}:9000"
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{MINIO_CONSOLE_PORT:-{base + 81}}}:9001"
    volumes:
      - minio-data:/data

volumes:
  minio-data:
'''

    @staticmethod
    def _render_env(specification: ProjectSpec) -> str:
        base = specification.tooling.storage.host_port_base
        return f'''# Copy to .env and replace these local development credentials.
LOCAL_BIND_ADDRESS=127.0.0.1
MINIO_ROOT_USER=autoforge
MINIO_ROOT_PASSWORD=change-me
MINIO_API_PORT={base + 80}
MINIO_CONSOLE_PORT={base + 81}
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=autoforge
S3_SECRET_KEY=change-me
'''

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        return f'''# Generated local object storage

This optional overlay provides an S3-compatible MinIO endpoint for
`{specification.project.package_name}`. It does not create buckets, retention
rules, object schemas, or application upload code.

```powershell
Copy-Item deploy/storage/.env.example deploy/storage/.env
docker compose --env-file deploy/storage/.env -f deploy/storage/compose.storage.yaml --profile storage up -d
docker compose --env-file deploy/storage/.env -f deploy/storage/compose.storage.yaml --profile storage down
```

The S3-compatible in-network endpoint is `S3_ENDPOINT_URL`. MinIO data uses a
named Docker volume and the API/console bind to `LOCAL_BIND_ADDRESS` only.
Replace the sample root credentials before starting the profile. Production
requires separate credentials, encrypted backups, bucket policies, lifecycle
rules, and a cluster-aware object-storage deployment; do not use this Compose
file as a production topology.
'''
