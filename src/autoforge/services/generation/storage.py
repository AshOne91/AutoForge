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
MINIO_CLIENT_IMAGE = "minio/mc:RELEASE.2025-08-13T08-35-41Z"


class ObjectStorageGenerator:
    """Generate local S3-compatible storage and an opt-in runtime boundary."""

    @property
    def generator_id(self) -> str:
        return OBJECT_STORAGE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return OBJECT_STORAGE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        storage = specification.tooling.storage
        if not storage.enabled and not storage.runtime_enabled:
            return {}
        rendered: dict[PurePosixPath, str] = {}
        if storage.enabled:
            rendered.update(
                {
                    PurePosixPath(
                        "deploy", "storage", "compose.storage.yaml"
                    ): self._render_compose(specification),
                    PurePosixPath("deploy", "storage", ".env.example"): self._render_env(
                        specification
                    ),
                    PurePosixPath("deploy", "storage", "README.md"): self._render_readme(
                        specification
                    ),
                }
            )
        if storage.runtime_enabled:
            root = PurePosixPath(
                "src",
                specification.project.package_name,
                "infrastructure",
                "object_storage",
            )
            rendered.update(
                {
                    root / "__init__.py": self._render_runtime_init(),
                    root / "config.py": self._render_runtime_config(),
                    root / "protocol.py": self._render_runtime_protocol(),
                    root / "fake.py": self._render_runtime_fake(),
                    root / "s3.py": self._render_runtime_s3(),
                    root / "service.py": self._render_runtime_service(),
                }
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
    restart: unless-stopped
    environment:
      MINIO_ROOT_USER: ${{MINIO_ROOT_USER:?set MINIO_ROOT_USER}}
      MINIO_ROOT_PASSWORD: ${{MINIO_ROOT_PASSWORD:?set MINIO_ROOT_PASSWORD}}
    ports:
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{MINIO_API_PORT:-{base + 80}}}:9000"
      - "${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{MINIO_CONSOLE_PORT:-{base + 81}}}:9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 3s
      retries: 12

  minio-init:
    profiles: ["storage"]
    image: {MINIO_CLIENT_IMAGE}
    restart: "no"
    depends_on:
      minio:
        condition: service_healthy
    environment:
      MINIO_ROOT_USER: ${{MINIO_ROOT_USER:?set MINIO_ROOT_USER}}
      MINIO_ROOT_PASSWORD: ${{MINIO_ROOT_PASSWORD:?set MINIO_ROOT_PASSWORD}}
      S3_BUCKET: ${{S3_BUCKET:?set S3_BUCKET}}
    entrypoint:
      - /bin/sh
      - -ec
      - >
        mc alias set local http://minio:9000 "$${{MINIO_ROOT_USER}}" "$${{MINIO_ROOT_PASSWORD}}";
        mc mb --ignore-existing "local/$${{S3_BUCKET}}"

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
S3_BUCKET={specification.project.package_name.replace("_", "-")}-artifacts
S3_PREFIX=backups
'''

    @staticmethod
    def _render_readme(specification: ProjectSpec) -> str:
        return f'''# Generated local object storage

This generated overlay provides an S3-compatible MinIO endpoint for
`{specification.project.package_name}`. It does not configure retention rules,
object schemas, or application upload code.

```powershell
Copy-Item deploy/storage/.env.example deploy/storage/.env
docker compose --env-file deploy/storage/.env -f deploy/storage/compose.storage.yaml --profile storage up -d
docker compose --env-file deploy/storage/.env -f deploy/storage/compose.storage.yaml --profile storage down
```

The S3-compatible in-network endpoint is `S3_ENDPOINT_URL`. `minio-init`
idempotently creates `S3_BUCKET` after MinIO becomes healthy. MinIO data uses a
named Docker volume and the API/console bind to `LOCAL_BIND_ADDRESS` only.
`minio-init` exits successfully after initialization, so start this overlay with
`up -d` rather than adding it to a Compose `--wait` health gate.
Replace the sample root credentials before starting the profile. Production
requires separate credentials, encrypted backups, bucket policies, lifecycle
rules, and a cluster-aware object-storage deployment; do not use this Compose
file as a production topology.
'''

    @staticmethod
    def _render_runtime_init() -> str:
        return (
            "from .config import ObjectStorageConfig\n"
            "from .fake import FakeObjectStorageClient\n"
            "from .protocol import ObjectStorageClient\n"
            "from .s3 import Aioboto3ObjectStorageClient\n"
            "from .service import ObjectStorage\n"
            "\n"
            "__all__ = [\n"
            '    "Aioboto3ObjectStorageClient",\n'
            '    "FakeObjectStorageClient",\n'
            '    "ObjectStorage",\n'
            '    "ObjectStorageClient",\n'
            '    "ObjectStorageConfig",\n'
            "]\n"
        )

    @staticmethod
    def _render_runtime_config() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from urllib.parse import urlsplit\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class ObjectStorageConfig:\n"
            "    endpoint: str\n"
            "    bucket: str\n"
            "    prefix: str = ''\n"
            "    access_key: str | None = None\n"
            "    secret_key: str | None = None\n"
            "    region_name: str = 'us-east-1'\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> ObjectStorageConfig:\n"
            "        endpoint = os.environ.get('S3_ENDPOINT_URL')\n"
            "        bucket = os.environ.get('S3_BUCKET')\n"
            "        if not endpoint or not bucket:\n"
            "            raise RuntimeError('S3_ENDPOINT_URL and S3_BUCKET must be set')\n"
            "        return cls(\n"
            "            endpoint=endpoint,\n"
            "            bucket=bucket,\n"
            "            prefix=os.environ.get('S3_PREFIX', ''),\n"
            "            access_key=os.environ.get('S3_ACCESS_KEY'),\n"
            "            secret_key=os.environ.get('S3_SECRET_KEY'),\n"
            "            region_name=os.environ.get('S3_REGION', 'us-east-1'),\n"
            "        )\n"
            "\n"
            "    def __post_init__(self) -> None:\n"
            "        parsed = urlsplit(self.endpoint)\n"
            "        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:\n"
            "            raise ValueError('S3 endpoint must be an absolute HTTP(S) URL')\n"
            "        if parsed.query or parsed.fragment or parsed.username or parsed.password:\n"
            "            raise ValueError('S3 endpoint must not contain credentials or query data')\n"
            "        if not self.bucket or self.bucket != self.bucket.strip() or '/' in self.bucket:\n"
            "            raise ValueError('S3 bucket must be a non-empty name')\n"
            "        if (self.access_key is None) != (self.secret_key is None):\n"
            "            raise ValueError('S3 credentials must be provided together')\n"
            "        object.__setattr__(self, 'prefix', self.prefix.strip('/'))\n"
        )

    @staticmethod
    def _render_runtime_protocol() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class ObjectStorageClient(Protocol):\n"
            "    async def health_check(self) -> None: ...\n"
            "\n"
            "    async def put_bytes(\n"
            "        self, key: str, content: bytes, *, content_type: str | None = None\n"
            "    ) -> None: ...\n"
            "\n"
            "    async def get_bytes(self, key: str) -> bytes | None: ...\n"
            "\n"
            "    async def delete(self, key: str) -> None: ...\n"
            "\n"
            "    async def list_keys(self, prefix: str = '') -> list[str]: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_runtime_fake() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "class FakeObjectStorageClient:\n"
            "    def __init__(self) -> None:\n"
            "        self._objects: dict[str, bytes] = {}\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def put_bytes(\n"
            "        self, key: str, content: bytes, *, content_type: str | None = None\n"
            "    ) -> None:\n"
            "        del content_type\n"
            "        self._objects[key] = bytes(content)\n"
            "\n"
            "    async def get_bytes(self, key: str) -> bytes | None:\n"
            "        return self._objects.get(key)\n"
            "\n"
            "    async def delete(self, key: str) -> None:\n"
            "        self._objects.pop(key, None)\n"
            "\n"
            "    async def list_keys(self, prefix: str = '') -> list[str]:\n"
            "        return sorted(key for key in self._objects if key.startswith(prefix))\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        )

    @staticmethod
    def _render_runtime_s3() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from contextlib import AsyncExitStack\n"
            "from importlib import import_module\n"
            "from typing import Any\n"
            "\n"
            "from .config import ObjectStorageConfig\n"
            "\n"
            "\n"
            "class Aioboto3ObjectStorageClient:\n"
            "    def __init__(self, config: ObjectStorageConfig) -> None:\n"
            "        self._config = config\n"
            "        self._stack: AsyncExitStack | None = None\n"
            "        self._client: Any = None\n"
            "\n"
            "    async def connect(self) -> None:\n"
            "        if self._client is not None:\n"
            "            return\n"
            "        try:\n"
            "            aioboto3 = import_module('aioboto3')\n"
            "        except ImportError as error:\n"
            "            raise RuntimeError(\n"
            "                'install aioboto3 to use the generated ObjectStorage client'\n"
            "            ) from error\n"
            "        client_kwargs: dict[str, str] = {\n"
            "            'service_name': 's3',\n"
            "            'region_name': self._config.region_name,\n"
            "            'endpoint_url': self._config.endpoint,\n"
            "        }\n"
            "        if self._config.access_key is not None:\n"
            "            client_kwargs.update(\n"
            "                aws_access_key_id=self._config.access_key,\n"
            "                aws_secret_access_key=self._config.secret_key or '',\n"
            "            )\n"
            "        self._stack = AsyncExitStack()\n"
            "        self._client = await self._stack.enter_async_context(\n"
            "            aioboto3.Session().client(**client_kwargs)\n"
            "        )\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._require_client().head_bucket(Bucket=self._config.bucket)\n"
            "\n"
            "    async def put_bytes(\n"
            "        self, key: str, content: bytes, *, content_type: str | None = None\n"
            "    ) -> None:\n"
            "        request: dict[str, object] = {\n"
            "            'Bucket': self._config.bucket,\n"
            "            'Key': self._object_key(key),\n"
            "            'Body': content,\n"
            "        }\n"
            "        if content_type is not None:\n"
            "            request['ContentType'] = content_type\n"
            "        await self._require_client().put_object(**request)\n"
            "\n"
            "    async def get_bytes(self, key: str) -> bytes | None:\n"
            "        try:\n"
            "            response = await self._require_client().get_object(\n"
            "                Bucket=self._config.bucket, Key=self._object_key(key)\n"
            "            )\n"
            "        except Exception as error:\n"
            "            if self._is_missing_object(error):\n"
            "                return None\n"
            "            raise\n"
            "        return await response['Body'].read()\n"
            "\n"
            "    async def delete(self, key: str) -> None:\n"
            "        await self._require_client().delete_object(\n"
            "            Bucket=self._config.bucket, Key=self._object_key(key)\n"
            "        )\n"
            "\n"
            "    async def list_keys(self, prefix: str = '') -> list[str]:\n"
            "        paginator = self._require_client().get_paginator('list_objects_v2')\n"
            "        keys: list[str] = []\n"
            "        async for page in paginator.paginate(\n"
            "            Bucket=self._config.bucket, Prefix=self._object_key(prefix, allow_empty=True)\n"
            "        ):\n"
            "            for item in page.get('Contents', []):\n"
            "                key = item.get('Key')\n"
            "                if isinstance(key, str):\n"
            "                    logical_key = self._logical_key(key)\n"
            "                    if logical_key is not None:\n"
            "                        keys.append(logical_key)\n"
            "        return keys\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        if self._stack is not None:\n"
            "            await self._stack.aclose()\n"
            "        self._stack = None\n"
            "        self._client = None\n"
            "\n"
            "    def _object_key(self, key: str, *, allow_empty: bool = False) -> str:\n"
            "        normalized = key.strip('/')\n"
            "        if not normalized and not allow_empty:\n"
            "            raise ValueError('object key must not be empty')\n"
            "        if any(part == '..' for part in normalized.split('/')):\n"
            "            raise ValueError('object key must not contain parent traversal')\n"
            "        parts = [part for part in (self._config.prefix, normalized) if part]\n"
            "        return '/'.join(parts)\n"
            "\n"
            "    def _logical_key(self, key: str) -> str | None:\n"
            "        prefix = self._config.prefix\n"
            "        if not prefix:\n"
            "            return key\n"
            "        if not key.startswith(f'{prefix}/'):\n"
            "            return None\n"
            "        return key[len(prefix) + 1:]\n"
            "\n"
            "    @staticmethod\n"
            "    def _is_missing_object(error: Exception) -> bool:\n"
            "        response = getattr(error, 'response', None)\n"
            "        if not isinstance(response, dict):\n"
            "            return False\n"
            "        code = response.get('Error', {}).get('Code')\n"
            "        return code in {'NoSuchKey', 'NoSuchObject', '404'}\n"
            "\n"
            "    def _require_client(self) -> Any:\n"
            "        if self._client is None:\n"
            "            raise RuntimeError('ObjectStorage must be connected before use')\n"
            "        return self._client\n"
        )

    @staticmethod
    def _render_runtime_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from .config import ObjectStorageConfig\n"
            "from .protocol import ObjectStorageClient\n"
            "\n"
            "\n"
            "class ObjectStorage:\n"
            "    def __init__(self, client: ObjectStorageClient) -> None:\n"
            "        self._client = client\n"
            "\n"
            "    @classmethod\n"
            "    async def from_environment(cls) -> ObjectStorage:\n"
            "        from .s3 import Aioboto3ObjectStorageClient\n"
            "\n"
            "        client = Aioboto3ObjectStorageClient(\n"
            "            ObjectStorageConfig.from_environment()\n"
            "        )\n"
            "        await client.connect()\n"
            "        return cls(client)\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._client.health_check()\n"
            "\n"
            "    async def put_bytes(\n"
            "        self, key: str, content: bytes, *, content_type: str | None = None\n"
            "    ) -> None:\n"
            "        await self._client.put_bytes(key, content, content_type=content_type)\n"
            "\n"
            "    async def get_bytes(self, key: str) -> bytes | None:\n"
            "        return await self._client.get_bytes(key)\n"
            "\n"
            "    async def delete(self, key: str) -> None:\n"
            "        await self._client.delete(key)\n"
            "\n"
            "    async def list_keys(self, prefix: str = '') -> list[str]:\n"
            "        return await self._client.list_keys(prefix)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )
