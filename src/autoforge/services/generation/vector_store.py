import json
from pathlib import PurePosixPath
from typing import Final

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import ProjectSpec, VectorStoreSpec

VECTOR_STORE_GENERATOR_ID: Final = "autoforge.generator.service.vector_store"
VECTOR_STORE_GENERATOR_VERSION: Final = "0.1.0"


class VectorStoreGenerator:
    """Generate an async Qdrant vector-store service boundary."""

    @property
    def generator_id(self) -> str:
        return VECTOR_STORE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return VECTOR_STORE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        vector_store = specification.tooling.vector_store
        if not vector_store.enabled:
            return {}

        root = PurePosixPath(
            "src",
            specification.project.package_name,
            "infrastructure",
            "vector_store",
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(vector_store),
            root / "protocol.py": self._render_protocol(),
            root / "fake.py": self._render_fake(),
            root / "qdrant.py": self._render_qdrant(),
            root / "service.py": self._render_service(),
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
                    source=(
                        f"project:{specification.project.package_name}:vector-store"
                    ),
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .config import VectorStoreConfig\n"
            "from .fake import FakeVectorStoreClient\n"
            "from .protocol import VectorStoreClient\n"
            "from .qdrant import QdrantVectorStoreClient\n"
            "from .service import VectorStore\n"
            "\n"
            "__all__ = [\n"
            '    "FakeVectorStoreClient",\n'
            '    "QdrantVectorStoreClient",\n'
            '    "VectorStore",\n'
            '    "VectorStoreClient",\n'
            '    "VectorStoreConfig",\n'
            "]\n"
        )

    @staticmethod
    def _render_config(vector_store: VectorStoreSpec) -> str:
        api_key_environment = (
            json.dumps(vector_store.api_key_environment)
            if vector_store.api_key_environment is not None
            else "None"
        )
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from typing import Final\n"
            "\n"
            f"VECTOR_STORE_URL_ENV: Final = {json.dumps(vector_store.url_environment)}\n"
            f"VECTOR_STORE_API_KEY_ENV: Final = {api_key_environment}\n"
            f"DEFAULT_COLLECTION: Final = {json.dumps(vector_store.default_collection)}\n"
            f"DEFAULT_TIMEOUT_SECONDS: Final = {vector_store.timeout_seconds!r}\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class VectorStoreConfig:\n"
            "    base_url: str\n"
            "    default_collection: str = DEFAULT_COLLECTION\n"
            "    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n"
            "    api_key: str | None = None\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> VectorStoreConfig:\n"
            "        base_url = os.environ.get(VECTOR_STORE_URL_ENV)\n"
            "        if not base_url:\n"
            "            raise RuntimeError(f'{VECTOR_STORE_URL_ENV} must be set')\n"
            "        api_key = (\n"
            "            os.environ.get(VECTOR_STORE_API_KEY_ENV)\n"
            "            if VECTOR_STORE_API_KEY_ENV\n"
            "            else None\n"
            "        )\n"
            "        return cls(base_url=base_url.rstrip('/'), api_key=api_key)\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping, Sequence\n"
            "from typing import Protocol\n"
            "\n"
            "type PointId = int | str\n"
            "\n"
            "\n"
            "class VectorStoreClient(Protocol):\n"
            "    async def health_check(self) -> None: ...\n"
            "\n"
            "    async def upsert_point(\n"
            "        self,\n"
            "        collection: str,\n"
            "        point_id: PointId,\n"
            "        vector: Sequence[float],\n"
            "        payload: Mapping[str, object],\n"
            "    ) -> None: ...\n"
            "\n"
            "    async def delete_point(self, collection: str, point_id: PointId) -> None: ...\n"
            "\n"
            "    async def get_point(\n"
            "        self, collection: str, point_id: PointId\n"
            "    ) -> dict[str, object] | None: ...\n"
            "\n"
            "    async def query(\n"
            "        self, collection: str, query: Mapping[str, object]\n"
            "    ) -> list[dict[str, object]]: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping, Sequence\n"
            "\n"
            "from .protocol import PointId\n"
            "\n"
            "\n"
            "class FakeVectorStoreClient:\n"
            "    \"\"\"Deterministic transport fake; vector relevance belongs to the consumer.\"\"\"\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self._points: dict[tuple[str, PointId], dict[str, object]] = {}\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def upsert_point(\n"
            "        self,\n"
            "        collection: str,\n"
            "        point_id: PointId,\n"
            "        vector: Sequence[float],\n"
            "        payload: Mapping[str, object],\n"
            "    ) -> None:\n"
            "        self._points[collection, point_id] = {\n"
            "            'id': point_id,\n"
            "            'vector': list(vector),\n"
            "            'payload': dict(payload),\n"
            "        }\n"
            "\n"
            "    async def delete_point(self, collection: str, point_id: PointId) -> None:\n"
            "        self._points.pop((collection, point_id), None)\n"
            "\n"
            "    async def get_point(\n"
            "        self, collection: str, point_id: PointId\n"
            "    ) -> dict[str, object] | None:\n"
            "        point = self._points.get((collection, point_id))\n"
            "        return dict(point) if point is not None else None\n"
            "\n"
            "    async def query(\n"
            "        self, collection: str, query: Mapping[str, object]\n"
            "    ) -> list[dict[str, object]]:\n"
            "        del query\n"
            "        return [\n"
            "            dict(point)\n"
            "            for (stored_collection, _), point in sorted(\n"
            "                self._points.items(), key=lambda item: str(item[0])\n"
            "            )\n"
            "            if stored_collection == collection\n"
            "        ]\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        )

    @staticmethod
    def _render_qdrant() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping, Sequence\n"
            "from urllib.parse import quote\n"
            "\n"
            "import httpx\n"
            "\n"
            "from .config import VectorStoreConfig\n"
            "from .protocol import PointId\n"
            "\n"
            "\n"
            "class QdrantVectorStoreClient:\n"
            "    def __init__(self, config: VectorStoreConfig) -> None:\n"
            "        headers = {'api-key': config.api_key} if config.api_key else {}\n"
            "        self._client = httpx.AsyncClient(\n"
            "            base_url=config.base_url,\n"
            "            timeout=config.timeout_seconds,\n"
            "            headers=headers,\n"
            "        )\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        response = await self._client.get('/readyz')\n"
            "        response.raise_for_status()\n"
            "\n"
            "    async def upsert_point(\n"
            "        self,\n"
            "        collection: str,\n"
            "        point_id: PointId,\n"
            "        vector: Sequence[float],\n"
            "        payload: Mapping[str, object],\n"
            "    ) -> None:\n"
            "        response = await self._client.put(\n"
            "            f'/{self._collection_path(collection)}/points',\n"
            "            params={'wait': 'true'},\n"
            "            json={\n"
            "                'points': [\n"
            "                    {\n"
            "                        'id': point_id,\n"
            "                        'vector': list(vector),\n"
            "                        'payload': dict(payload),\n"
            "                    }\n"
            "                ]\n"
            "            },\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "\n"
            "    async def delete_point(self, collection: str, point_id: PointId) -> None:\n"
            "        response = await self._client.post(\n"
            "            f'/{self._collection_path(collection)}/points/delete',\n"
            "            params={'wait': 'true'},\n"
            "            json={'points': [point_id]},\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "\n"
            "    async def get_point(\n"
            "        self, collection: str, point_id: PointId\n"
            "    ) -> dict[str, object] | None:\n"
            "        response = await self._client.get(\n"
            "            f'/{self._collection_path(collection)}/points/{quote(str(point_id), safe=\"\")}'\n"
            "        )\n"
            "        if response.status_code == 404:\n"
            "            return None\n"
            "        response.raise_for_status()\n"
            "        result = response.json().get('result')\n"
            "        return dict(result) if isinstance(result, dict) else None\n"
            "\n"
            "    async def query(\n"
            "        self, collection: str, query: Mapping[str, object]\n"
            "    ) -> list[dict[str, object]]:\n"
            "        response = await self._client.post(\n"
            "            f'/{self._collection_path(collection)}/points/query', json=dict(query)\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "        result = response.json().get('result', {})\n"
            "        points = result.get('points', []) if isinstance(result, dict) else []\n"
            "        return [dict(point) for point in points if isinstance(point, dict)]\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
            "\n"
            "    @staticmethod\n"
            "    def _collection_path(collection: str) -> str:\n"
            "        return f'collections/{quote(collection, safe=\"\")}'\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping, Sequence\n"
            "\n"
            "from .config import VectorStoreConfig\n"
            "from .protocol import PointId, VectorStoreClient\n"
            "\n"
            "\n"
            "class VectorStore:\n"
            "    def __init__(self, client: VectorStoreClient, default_collection: str) -> None:\n"
            "        self._client = client\n"
            "        self._default_collection = default_collection\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> VectorStore:\n"
            "        from .qdrant import QdrantVectorStoreClient\n"
            "\n"
            "        config = VectorStoreConfig.from_environment()\n"
            "        return cls(QdrantVectorStoreClient(config), config.default_collection)\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._client.health_check()\n"
            "\n"
            "    async def upsert_point(\n"
            "        self,\n"
            "        point_id: PointId,\n"
            "        vector: Sequence[float],\n"
            "        payload: Mapping[str, object],\n"
            "        *,\n"
            "        collection: str | None = None,\n"
            "    ) -> None:\n"
            "        await self._client.upsert_point(\n"
            "            collection or self._default_collection, point_id, vector, payload\n"
            "        )\n"
            "\n"
            "    async def delete_point(\n"
            "        self, point_id: PointId, *, collection: str | None = None\n"
            "    ) -> None:\n"
            "        await self._client.delete_point(\n"
            "            collection or self._default_collection, point_id\n"
            "        )\n"
            "\n"
            "    async def get_point(\n"
            "        self, point_id: PointId, *, collection: str | None = None\n"
            "    ) -> dict[str, object] | None:\n"
            "        return await self._client.get_point(\n"
            "            collection or self._default_collection, point_id\n"
            "        )\n"
            "\n"
            "    async def query(\n"
            "        self, query: Mapping[str, object], *, collection: str | None = None\n"
            "    ) -> list[dict[str, object]]:\n"
            "        return await self._client.query(\n"
            "            collection or self._default_collection, query\n"
            "        )\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )
