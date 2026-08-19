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
from autoforge.core.specification import ExternalProviderSpec, ProjectSpec

EXTERNAL_PROVIDER_GENERATOR_ID: Final = "autoforge.generator.service.external_provider"
EXTERNAL_PROVIDER_GENERATOR_VERSION: Final = "0.1.0"


class ExternalProviderGenerator:
    """Generate an async external HTTP provider boundary."""

    @property
    def generator_id(self) -> str:
        return EXTERNAL_PROVIDER_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return EXTERNAL_PROVIDER_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        external_provider = specification.tooling.external_provider
        if not external_provider.enabled:
            return {}

        root = PurePosixPath(
            "src",
            specification.project.package_name,
            "infrastructure",
            "external_provider",
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(external_provider),
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
                        f"project:{specification.project.package_name}:external-provider"
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
            "from .config import ExternalProviderConfig\n"
            "from .fake import FakeExternalProviderClient\n"
            "from .http_client import HttpExternalProviderClient\n"
            "from .protocol import ExternalProviderClient, ExternalResponse\n"
            "from .service import ExternalProvider\n"
            "\n"
            "__all__ = [\n"
            '    "ExternalProvider",\n'
            '    "ExternalProviderClient",\n'
            '    "ExternalProviderConfig",\n'
            '    "ExternalResponse",\n'
            '    "FakeExternalProviderClient",\n'
            '    "HttpExternalProviderClient",\n'
            "]\n"
        )

    @staticmethod
    def _render_config(external_provider: ExternalProviderSpec) -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from typing import Final\n"
            "\n"
            f"EXTERNAL_PROVIDER_URL_ENV: Final = {json.dumps(external_provider.url_environment)}\n"
            f"DEFAULT_HEALTH_PATH: Final = {json.dumps(external_provider.health_path)}\n"
            f"DEFAULT_TIMEOUT_SECONDS: Final = {external_provider.timeout_seconds!r}\n"
            f"DEFAULT_MAX_RETRIES: Final = {external_provider.max_retries!r}\n"
            f"DEFAULT_RETRY_DELAY_SECONDS: Final = {external_provider.retry_delay_seconds!r}\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class ExternalProviderConfig:\n"
            "    base_url: str\n"
            "    health_path: str = DEFAULT_HEALTH_PATH\n"
            "    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n"
            "    max_retries: int = DEFAULT_MAX_RETRIES\n"
            "    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> ExternalProviderConfig:\n"
            "        base_url = os.environ.get(EXTERNAL_PROVIDER_URL_ENV)\n"
            "        if not base_url:\n"
            "            raise RuntimeError(f'{EXTERNAL_PROVIDER_URL_ENV} must be set')\n"
            "        return cls(base_url=base_url.rstrip('/'))\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping\n"
            "from dataclasses import dataclass\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class ExternalResponse:\n"
            "    status_code: int\n"
            "    headers: dict[str, str]\n"
            "    content: bytes\n"
            "\n"
            "\n"
            "class ExternalProviderClient(Protocol):\n"
            "    async def health_check(self) -> None: ...\n"
            "\n"
            "    async def request(\n"
            "        self,\n"
            "        method: str,\n"
            "        path: str,\n"
            "        *,\n"
            "        headers: Mapping[str, str] | None = None,\n"
            "        params: Mapping[str, str] | None = None,\n"
            "        json: object | None = None,\n"
            "        content: bytes | None = None,\n"
            "        retry_safe: bool | None = None,\n"
            "    ) -> ExternalResponse: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections import deque\n"
            "from collections.abc import Iterable, Mapping\n"
            "\n"
            "from .protocol import ExternalResponse\n"
            "\n"
            "\n"
            "class FakeExternalProviderClient:\n"
            "    \"\"\"Deterministic transport fake; provider semantics belong to the consumer.\"\"\"\n"
            "\n"
            "    def __init__(self, responses: Iterable[ExternalResponse] = ()) -> None:\n"
            "        self._responses = deque(responses)\n"
            "        self.requests: list[tuple[str, str]] = []\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def request(\n"
            "        self,\n"
            "        method: str,\n"
            "        path: str,\n"
            "        *,\n"
            "        headers: Mapping[str, str] | None = None,\n"
            "        params: Mapping[str, str] | None = None,\n"
            "        json: object | None = None,\n"
            "        content: bytes | None = None,\n"
            "        retry_safe: bool | None = None,\n"
            "    ) -> ExternalResponse:\n"
            "        del headers, params, json, content, retry_safe\n"
            "        self.requests.append((method.upper(), path))\n"
            "        if self._responses:\n"
            "            return self._responses.popleft()\n"
            "        return ExternalResponse(status_code=200, headers={}, content=b'')\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        )

    @staticmethod
    def _render_http_client() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import asyncio\n"
            "from collections.abc import Mapping\n"
            "\n"
            "import httpx\n"
            "\n"
            "from .config import ExternalProviderConfig\n"
            "from .protocol import ExternalResponse\n"
            "\n"
            "_DEFAULT_RETRY_SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})\n"
            "\n"
            "\n"
            "class HttpExternalProviderClient:\n"
            "    def __init__(\n"
            "        self,\n"
            "        config: ExternalProviderConfig,\n"
            "        *,\n"
            "        client: httpx.AsyncClient | None = None,\n"
            "    ) -> None:\n"
            "        self._config = config\n"
            "        self._client = client or httpx.AsyncClient(\n"
            "            base_url=config.base_url, timeout=config.timeout_seconds\n"
            "        )\n"
            "        self._owns_client = client is None\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        response = await self.request('GET', self._config.health_path)\n"
            "        if not 200 <= response.status_code < 400:\n"
            "            raise RuntimeError(\n"
            "                f'external provider health check returned {response.status_code}'\n"
            "            )\n"
            "\n"
            "    async def request(\n"
            "        self,\n"
            "        method: str,\n"
            "        path: str,\n"
            "        *,\n"
            "        headers: Mapping[str, str] | None = None,\n"
            "        params: Mapping[str, str] | None = None,\n"
            "        json: object | None = None,\n"
            "        content: bytes | None = None,\n"
            "        retry_safe: bool | None = None,\n"
            "    ) -> ExternalResponse:\n"
            "        if not path.startswith('/'):\n"
            "            raise ValueError('external provider path must start with /')\n"
            "        normalized_method = method.upper()\n"
            "        retries_allowed = (\n"
            "            retry_safe\n"
            "            if retry_safe is not None\n"
            "            else normalized_method in _DEFAULT_RETRY_SAFE_METHODS\n"
            "        )\n"
            "\n"
            "        for attempt in range(self._config.max_retries + 1):\n"
            "            try:\n"
            "                response = await self._client.request(\n"
            "                    normalized_method,\n"
            "                    path,\n"
            "                    headers=dict(headers) if headers else None,\n"
            "                    params=dict(params) if params else None,\n"
            "                    json=json,\n"
            "                    content=content,\n"
            "                )\n"
            "            except httpx.RequestError:\n"
            "                if not retries_allowed or attempt == self._config.max_retries:\n"
            "                    raise\n"
            "            else:\n"
            "                result = ExternalResponse(\n"
            "                    status_code=response.status_code,\n"
            "                    headers=dict(response.headers),\n"
            "                    content=response.content,\n"
            "                )\n"
            "                if (\n"
            "                    not retries_allowed\n"
            "                    or not self._is_retryable_status(result.status_code)\n"
            "                    or attempt == self._config.max_retries\n"
            "                ):\n"
            "                    return result\n"
            "\n"
            "            await asyncio.sleep(\n"
            "                self._config.retry_delay_seconds * (2**attempt)\n"
            "            )\n"
            "\n"
            "        raise AssertionError('request retry loop must return or raise')\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        if self._owns_client:\n"
            "            await self._client.aclose()\n"
            "\n"
            "    @staticmethod\n"
            "    def _is_retryable_status(status_code: int) -> bool:\n"
            "        return status_code in {408, 425, 429} or status_code >= 500\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Mapping\n"
            "\n"
            "from .config import ExternalProviderConfig\n"
            "from .protocol import ExternalProviderClient, ExternalResponse\n"
            "\n"
            "\n"
            "class ExternalProvider:\n"
            "    def __init__(self, client: ExternalProviderClient) -> None:\n"
            "        self._client = client\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> ExternalProvider:\n"
            "        from .http_client import HttpExternalProviderClient\n"
            "\n"
            "        return cls(HttpExternalProviderClient(ExternalProviderConfig.from_environment()))\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._client.health_check()\n"
            "\n"
            "    async def request(\n"
            "        self,\n"
            "        method: str,\n"
            "        path: str,\n"
            "        *,\n"
            "        headers: Mapping[str, str] | None = None,\n"
            "        params: Mapping[str, str] | None = None,\n"
            "        json: object | None = None,\n"
            "        content: bytes | None = None,\n"
            "        retry_safe: bool | None = None,\n"
            "    ) -> ExternalResponse:\n"
            "        return await self._client.request(\n"
            "            method,\n"
            "            path,\n"
            "            headers=headers,\n"
            "            params=params,\n"
            "            json=json,\n"
            "            content=content,\n"
            "            retry_safe=retry_safe,\n"
            "        )\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )
