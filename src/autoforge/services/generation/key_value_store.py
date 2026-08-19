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
from autoforge.core.specification import KeyValueStoreSpec, ProjectSpec

KEY_VALUE_STORE_GENERATOR_ID: Final = "autoforge.generator.service.key_value_store"
KEY_VALUE_STORE_GENERATOR_VERSION: Final = "0.1.0"


class KeyValueStoreGenerator:
    """Generate an async Redis key-value store boundary."""

    @property
    def generator_id(self) -> str:
        return KEY_VALUE_STORE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return KEY_VALUE_STORE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        key_value_store = specification.tooling.key_value_store
        if not key_value_store.enabled:
            return {}

        root = PurePosixPath(
            "src",
            specification.project.package_name,
            "infrastructure",
            "key_value_store",
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(key_value_store),
            root / "protocol.py": self._render_protocol(),
            root / "fake.py": self._render_fake(),
            root / "redis.py": self._render_redis(),
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
                        f"project:{specification.project.package_name}:key-value-store"
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
            "from .config import KeyValueStoreConfig, RedisMode\n"
            "from .fake import FakeKeyValueStoreClient\n"
            "from .protocol import KeyValueStoreClient\n"
            "from .redis import RedisKeyValueStoreClient\n"
            "from .service import KeyValueStore\n"
            "\n"
            "__all__ = [\n"
            '    "FakeKeyValueStoreClient",\n'
            '    "KeyValueStore",\n'
            '    "KeyValueStoreClient",\n'
            '    "KeyValueStoreConfig",\n'
            '    "RedisKeyValueStoreClient",\n'
            '    "RedisMode",\n'
            "]\n"
        )

    @staticmethod
    def _render_config(key_value_store: KeyValueStoreSpec) -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from enum import StrEnum\n"
            "from typing import Final\n"
            "\n"
            f"REDIS_URL_ENV: Final = {json.dumps(key_value_store.url_environment)}\n"
            f"REDIS_CLUSTER_URL_ENV: Final = {json.dumps(key_value_store.cluster_url_environment)}\n"
            f"REDIS_CLUSTER_STARTUP_NODES_ENV: Final = {json.dumps(key_value_store.cluster_startup_nodes_environment)}\n"
            f"REDIS_SENTINEL_URLS_ENV: Final = {json.dumps(key_value_store.sentinel_urls_environment)}\n"
            f"DEFAULT_MODE: Final = {json.dumps(key_value_store.mode)}\n"
            f"DEFAULT_SENTINEL_MASTER: Final = {json.dumps(key_value_store.sentinel_master)}\n"
            f"DEFAULT_KEY_PREFIX: Final = {json.dumps(key_value_store.key_prefix)}\n"
            f"DEFAULT_TTL_SECONDS: Final = {key_value_store.ttl_seconds!r}\n"
            "\n"
            "\n"
            "class RedisMode(StrEnum):\n"
            "    STANDALONE = 'standalone'\n"
            "    SENTINEL = 'sentinel'\n"
            "    CLUSTER = 'cluster'\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class KeyValueStoreConfig:\n"
            f"    mode: RedisMode = RedisMode.{key_value_store.mode.upper()}\n"
            "    redis_url: str = ''\n"
            "    cluster_startup_nodes: tuple[str, ...] = ()\n"
            "    sentinel_urls: str = ''\n"
            "    sentinel_master: str = DEFAULT_SENTINEL_MASTER\n"
            "    key_prefix: str = DEFAULT_KEY_PREFIX\n"
            "    ttl_seconds: int = DEFAULT_TTL_SECONDS\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> KeyValueStoreConfig:\n"
            "        mode = RedisMode(DEFAULT_MODE)\n"
            "        if mode is RedisMode.CLUSTER:\n"
            "            redis_url = _required_environment(REDIS_CLUSTER_URL_ENV)\n"
            "            startup_nodes = tuple(\n"
            "                value.strip()\n"
            "                for value in os.environ.get(REDIS_CLUSTER_STARTUP_NODES_ENV, '').split(',')\n"
            "                if value.strip()\n"
            "            )\n"
            "            return cls(\n"
            "                mode=mode, redis_url=redis_url, cluster_startup_nodes=startup_nodes\n"
            "            )\n"
            "        if mode is RedisMode.SENTINEL:\n"
            "            return cls(\n"
            "                mode=mode,\n"
            "                sentinel_urls=_required_environment(REDIS_SENTINEL_URLS_ENV),\n"
            "            )\n"
            "        return cls(mode=mode, redis_url=_required_environment(REDIS_URL_ENV))\n"
            "\n"
            "\n"
            "def _required_environment(name: str) -> str:\n"
            "    value = os.environ.get(name)\n"
            "    if not value:\n"
            "        raise RuntimeError(f'{name} must be set')\n"
            "    return value\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class KeyValueStoreClient(Protocol):\n"
            "    async def health_check(self) -> None: ...\n"
            "\n"
            "    async def get(self, key: str) -> str | None: ...\n"
            "\n"
            "    async def set(\n"
            "        self, key: str, value: str, *, ttl_seconds: int | None = None\n"
            "    ) -> None: ...\n"
            "\n"
            "    async def delete(self, key: str) -> bool: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from collections.abc import Callable\n"
            "from time import monotonic\n"
            "\n"
            "\n"
            "class FakeKeyValueStoreClient:\n"
            "    \"\"\"Deterministic TTL key-value fake.\"\"\"\n"
            "\n"
            "    def __init__(\n"
            "        self,\n"
            "        default_ttl_seconds: int,\n"
            "        clock: Callable[[], float] = monotonic,\n"
            "    ) -> None:\n"
            "        if default_ttl_seconds <= 0:\n"
            "            raise ValueError('default_ttl_seconds must be positive')\n"
            "        self._default_ttl_seconds = default_ttl_seconds\n"
            "        self._clock = clock\n"
            "        self._values: dict[str, tuple[str, float]] = {}\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def get(self, key: str) -> str | None:\n"
            "        self._require_key(key)\n"
            "        stored = self._values.get(key)\n"
            "        if stored is None:\n"
            "            return None\n"
            "        value, expires_at = stored\n"
            "        if expires_at <= self._clock():\n"
            "            del self._values[key]\n"
            "            return None\n"
            "        return value\n"
            "\n"
            "    async def set(\n"
            "        self, key: str, value: str, *, ttl_seconds: int | None = None\n"
            "    ) -> None:\n"
            "        self._require_key(key)\n"
            "        self._values[key] = (value, self._clock() + self._ttl(ttl_seconds))\n"
            "\n"
            "    async def delete(self, key: str) -> bool:\n"
            "        self._require_key(key)\n"
            "        return self._values.pop(key, None) is not None\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
            "\n"
            "    def _ttl(self, ttl_seconds: int | None) -> int:\n"
            "        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds\n"
            "        if ttl <= 0:\n"
            "            raise ValueError('ttl_seconds must be positive')\n"
            "        return ttl\n"
            "\n"
            "    @staticmethod\n"
            "    def _require_key(key: str) -> None:\n"
            "        if not key:\n"
            "            raise ValueError('cache key must not be empty')\n"
        )

    @staticmethod
    def _render_redis() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from urllib.parse import urlparse\n"
            "\n"
            "from redis.asyncio import Redis\n"
            "from redis.asyncio.cluster import RedisCluster\n"
            "from redis.asyncio.sentinel import Sentinel\n"
            "from redis.cluster import ClusterNode\n"
            "\n"
            "from .config import KeyValueStoreConfig, RedisMode\n"
            "\n"
            "\n"
            "class RedisKeyValueStoreClient:\n"
            "    def __init__(\n"
            "        self, config: KeyValueStoreConfig, *, client: Redis | RedisCluster | None = None\n"
            "    ) -> None:\n"
            "        self._config = config\n"
            "        self._sentinel: Sentinel | None = None\n"
            "        if client is not None:\n"
            "            self._client = client\n"
            "            self._owns_client = False\n"
            "        elif config.mode is RedisMode.CLUSTER:\n"
            "            self._client = RedisCluster.from_url(\n"
            "                config.redis_url,\n"
            "                startup_nodes=self._cluster_startup_nodes() or None,\n"
            "                decode_responses=True,\n"
            "                require_full_coverage=True,\n"
            "                reinitialize_steps=1,\n"
            "            )\n"
            "            self._owns_client = True\n"
            "        elif config.mode is RedisMode.SENTINEL:\n"
            "            self._sentinel = Sentinel(\n"
            "                self._sentinel_endpoints(config.sentinel_urls),\n"
            "                socket_timeout=2, decode_responses=True\n"
            "            )\n"
            "            self._client = self._sentinel.master_for(\n"
            "                config.sentinel_master, socket_timeout=2, decode_responses=True\n"
            "            )\n"
            "            self._owns_client = True\n"
            "        else:\n"
            "            self._client = Redis.from_url(config.redis_url, decode_responses=True)\n"
            "            self._owns_client = True\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        if not await self._client.ping():\n"
            "            raise RuntimeError('Redis key-value store health check failed')\n"
            "\n"
            "    async def get(self, key: str) -> str | None:\n"
            "        return await self._client.get(self._key(key))\n"
            "\n"
            "    async def set(\n"
            "        self, key: str, value: str, *, ttl_seconds: int | None = None\n"
            "    ) -> None:\n"
            "        await self._client.set(\n"
            "            self._key(key), value, ex=self._ttl(ttl_seconds)\n"
            "        )\n"
            "\n"
            "    async def delete(self, key: str) -> bool:\n"
            "        return bool(await self._client.delete(self._key(key)))\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        if self._owns_client:\n"
            "            await self._client.aclose()\n"
            "            if self._sentinel is not None:\n"
            "                for sentinel_client in self._sentinel.sentinels:\n"
            "                    await sentinel_client.aclose()\n"
            "\n"
            "    def _key(self, key: str) -> str:\n"
            "        if not key:\n"
            "            raise ValueError('cache key must not be empty')\n"
            "        return f'{self._config.key_prefix}:{key}'\n"
            "\n"
            "    def _ttl(self, ttl_seconds: int | None) -> int:\n"
            "        ttl = ttl_seconds if ttl_seconds is not None else self._config.ttl_seconds\n"
            "        if ttl <= 0:\n"
            "            raise ValueError('ttl_seconds must be positive')\n"
            "        return ttl\n"
            "\n"
            "    def _cluster_startup_nodes(self) -> list[ClusterNode]:\n"
            "        nodes: list[ClusterNode] = []\n"
            "        for value in self._config.cluster_startup_nodes:\n"
            "            parsed = urlparse(value)\n"
            "            if parsed.hostname:\n"
            "                nodes.append(ClusterNode(parsed.hostname, parsed.port or 6379))\n"
            "        return nodes\n"
            "\n"
            "    @staticmethod\n"
            "    def _sentinel_endpoints(value: str) -> list[tuple[str, int]]:\n"
            "        endpoints: list[tuple[str, int]] = []\n"
            "        for item in value.split(','):\n"
            "            host, separator, port_text = item.strip().rpartition(':')\n"
            "            if not separator or not host:\n"
            "                raise ValueError(f'Invalid Redis Sentinel endpoint: {item!r}')\n"
            "            try:\n"
            "                endpoints.append((host, int(port_text)))\n"
            "            except ValueError as error:\n"
            "                raise ValueError(\n"
            "                    f'Invalid Redis Sentinel port: {item!r}'\n"
            "                ) from error\n"
            "        if not endpoints:\n"
            "            raise ValueError('Redis Sentinel endpoints are empty')\n"
            "        return endpoints\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from .config import KeyValueStoreConfig\n"
            "from .protocol import KeyValueStoreClient\n"
            "\n"
            "\n"
            "class KeyValueStore:\n"
            "    def __init__(\n"
            "        self, client: KeyValueStoreClient, default_ttl_seconds: int\n"
            "    ) -> None:\n"
            "        self._client = client\n"
            "        self._default_ttl_seconds = default_ttl_seconds\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> KeyValueStore:\n"
            "        from .redis import RedisKeyValueStoreClient\n"
            "\n"
            "        config = KeyValueStoreConfig.from_environment()\n"
            "        return cls(RedisKeyValueStoreClient(config), config.ttl_seconds)\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._client.health_check()\n"
            "\n"
            "    async def get(self, key: str) -> str | None:\n"
            "        return await self._client.get(key)\n"
            "\n"
            "    async def set(\n"
            "        self, key: str, value: str, *, ttl_seconds: int | None = None\n"
            "    ) -> None:\n"
            "        await self._client.set(\n"
            "            key,\n"
            "            value,\n"
            "            ttl_seconds=(\n"
            "                self._default_ttl_seconds\n"
            "                if ttl_seconds is None\n"
            "                else ttl_seconds\n"
            "            ),\n"
            "        )\n"
            "\n"
            "    async def delete(self, key: str) -> bool:\n"
            "        return await self._client.delete(key)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )
