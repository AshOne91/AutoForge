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
from autoforge.core.specification import ProjectSpec, SearchSpec

SEARCH_SERVICE_GENERATOR_ID: Final = "autoforge.generator.service.search"
SEARCH_SERVICE_GENERATOR_VERSION: Final = "0.1.0"


class SearchServiceGenerator:
    """Generate an async Elasticsearch/OpenSearch service boundary."""

    @property
    def generator_id(self) -> str:
        return SEARCH_SERVICE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return SEARCH_SERVICE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        search = specification.tooling.search
        if not search.enabled:
            return {}

        root = PurePosixPath(
            "src", specification.project.package_name, "infrastructure", "search"
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(search),
            root / "protocol.py": self._render_protocol(),
            root / "fake.py": self._render_fake(),
            root / "http_client.py": self._render_http_client(),
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
                        f"project:{specification.project.package_name}:search-service"
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
            "from .config import SearchBackend, SearchConfig\n"
            "from .fake import FakeSearchClient\n"
            "from .http_client import HttpSearchClient\n"
            "from .protocol import SearchClient\n"
            "from .service import SearchService\n"
            "\n"
            "__all__ = [\n"
            '    "FakeSearchClient",\n'
            '    "HttpSearchClient",\n'
            '    "SearchBackend",\n'
            '    "SearchClient",\n'
            '    "SearchConfig",\n'
            '    "SearchService",\n'
            "]\n"
        )

    @staticmethod
    def _render_config(search: SearchSpec) -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from enum import StrEnum\n"
            "from typing import Final\n"
            "\n"
            f"SEARCH_URL_ENV: Final = {json.dumps(search.url_environment)}\n"
            f"DEFAULT_INDEX: Final = {json.dumps(search.default_index)}\n"
            f"DEFAULT_TIMEOUT_SECONDS: Final = {search.timeout_seconds!r}\n"
            f"DEFAULT_BACKEND: Final = {json.dumps(search.backend)}\n"
            "\n"
            "\n"
            "class SearchBackend(StrEnum):\n"
            "    ELASTICSEARCH = 'elasticsearch'\n"
            "    OPENSEARCH = 'opensearch'\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class SearchConfig:\n"
            "    base_url: str\n"
            "    backend: SearchBackend\n"
            "    default_index: str = DEFAULT_INDEX\n"
            "    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> SearchConfig:\n"
            "        base_url = os.environ.get(SEARCH_URL_ENV)\n"
            "        if not base_url:\n"
            "            raise RuntimeError(f'{SEARCH_URL_ENV} must be set')\n"
            "        return cls(\n"
            "            base_url=base_url.rstrip('/'),\n"
            "            backend=SearchBackend(DEFAULT_BACKEND),\n"
            "        )\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class SearchClient(Protocol):\n"
            "    async def health_check(self) -> None: ...\n"
            "\n"
            "    async def index_document(\n"
            "        self, index: str, document_id: str, document: Mapping[str, object]\n"
            "    ) -> None: ...\n"
            "\n"
            "    async def delete_document(self, index: str, document_id: str) -> None: ...\n"
            "\n"
            "    async def search(\n"
            "        self, index: str, query: Mapping[str, object]\n"
            "    ) -> list[dict[str, object]]: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping\n"
            "\n"
            "\n"
            "class FakeSearchClient:\n"
            "    \"\"\"Deterministic transport fake; query relevance belongs to the consumer.\"\"\"\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self._documents: dict[tuple[str, str], dict[str, object]] = {}\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def index_document(\n"
            "        self, index: str, document_id: str, document: Mapping[str, object]\n"
            "    ) -> None:\n"
            "        self._documents[index, document_id] = dict(document)\n"
            "\n"
            "    async def delete_document(self, index: str, document_id: str) -> None:\n"
            "        self._documents.pop((index, document_id), None)\n"
            "\n"
            "    async def search(\n"
            "        self, index: str, query: Mapping[str, object]\n"
            "    ) -> list[dict[str, object]]:\n"
            "        del query\n"
            "        return [\n"
            "            dict(document)\n"
            "            for (stored_index, _), document in sorted(self._documents.items())\n"
            "            if stored_index == index\n"
            "        ]\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        )

    @staticmethod
    def _render_http_client() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping\n"
            "from urllib.parse import quote\n"
            "\n"
            "import httpx\n"
            "\n"
            "from .config import SearchConfig\n"
            "\n"
            "\n"
            "class HttpSearchClient:\n"
            "    def __init__(self, config: SearchConfig) -> None:\n"
            "        self._client = httpx.AsyncClient(\n"
            "            base_url=config.base_url, timeout=config.timeout_seconds\n"
            "        )\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        response = await self._client.get('/_cluster/health')\n"
            "        response.raise_for_status()\n"
            "\n"
            "    async def index_document(\n"
            "        self, index: str, document_id: str, document: Mapping[str, object]\n"
            "    ) -> None:\n"
            "        response = await self._client.put(\n"
            "            f'/{quote(index, safe=\"\")}/_doc/{quote(document_id, safe=\"\")}',\n"
            "            json=dict(document),\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "\n"
            "    async def delete_document(self, index: str, document_id: str) -> None:\n"
            "        response = await self._client.delete(\n"
            "            f'/{quote(index, safe=\"\")}/_doc/{quote(document_id, safe=\"\")}'\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "\n"
            "    async def search(\n"
            "        self, index: str, query: Mapping[str, object]\n"
            "    ) -> list[dict[str, object]]:\n"
            "        response = await self._client.post(\n"
            "            f'/{quote(index, safe=\"\")}/_search', json=dict(query)\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "        payload = response.json()\n"
            "        hits = payload.get('hits', {}).get('hits', [])\n"
            "        return [dict(hit) for hit in hits if isinstance(hit, dict)]\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping\n"
            "\n"
            "from .config import SearchConfig\n"
            "from .protocol import SearchClient\n"
            "\n"
            "\n"
            "class SearchService:\n"
            "    def __init__(self, client: SearchClient, default_index: str) -> None:\n"
            "        self._client = client\n"
            "        self._default_index = default_index\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> SearchService:\n"
            "        from .http_client import HttpSearchClient\n"
            "\n"
            "        config = SearchConfig.from_environment()\n"
            "        return cls(HttpSearchClient(config), config.default_index)\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._client.health_check()\n"
            "\n"
            "    async def index_document(\n"
            "        self, document_id: str, document: Mapping[str, object], *, index: str | None = None\n"
            "    ) -> None:\n"
            "        await self._client.index_document(index or self._default_index, document_id, document)\n"
            "\n"
            "    async def delete_document(\n"
            "        self, document_id: str, *, index: str | None = None\n"
            "    ) -> None:\n"
            "        await self._client.delete_document(index or self._default_index, document_id)\n"
            "\n"
            "    async def search(\n"
            "        self, query: Mapping[str, object], *, index: str | None = None\n"
            "    ) -> list[dict[str, object]]:\n"
            "        return await self._client.search(index or self._default_index, query)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )
