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
from autoforge.core.specification import DistributedLockSpec, ProjectSpec

DISTRIBUTED_LOCK_GENERATOR_ID: Final = "autoforge.generator.service.distributed_lock"
DISTRIBUTED_LOCK_GENERATOR_VERSION: Final = "0.1.0"


class DistributedLockGenerator:
    """Generate an async Redis distributed-lock boundary."""

    @property
    def generator_id(self) -> str:
        return DISTRIBUTED_LOCK_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return DISTRIBUTED_LOCK_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        distributed_lock = specification.tooling.distributed_lock
        if not distributed_lock.enabled:
            return {}

        root = PurePosixPath(
            "src",
            specification.project.package_name,
            "infrastructure",
            "distributed_lock",
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(distributed_lock),
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
                        f"project:{specification.project.package_name}:distributed-lock"
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
            "from .config import DistributedLockConfig, RedisMode\n"
            "from .fake import FakeDistributedLockClient\n"
            "from .protocol import DistributedLockClient\n"
            "from .redis import RedisDistributedLockClient\n"
            "from .service import DistributedLock\n"
            "\n"
            "__all__ = [\n"
            '    "DistributedLock",\n'
            '    "DistributedLockClient",\n'
            '    "DistributedLockConfig",\n'
            '    "FakeDistributedLockClient",\n'
            '    "RedisDistributedLockClient",\n'
            '    "RedisMode",\n'
            "]\n"
        )

    @staticmethod
    def _render_config(distributed_lock: DistributedLockSpec) -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from enum import StrEnum\n"
            "from typing import Final\n"
            "\n"
            f"REDIS_URL_ENV: Final = {json.dumps(distributed_lock.url_environment)}\n"
            f"REDIS_CLUSTER_URL_ENV: Final = {json.dumps(distributed_lock.cluster_url_environment)}\n"
            f"REDIS_CLUSTER_STARTUP_NODES_ENV: Final = {json.dumps(distributed_lock.cluster_startup_nodes_environment)}\n"
            f"REDIS_SENTINEL_URLS_ENV: Final = {json.dumps(distributed_lock.sentinel_urls_environment)}\n"
            f"DEFAULT_MODE: Final = {json.dumps(distributed_lock.mode)}\n"
            f"DEFAULT_SENTINEL_MASTER: Final = {json.dumps(distributed_lock.sentinel_master)}\n"
            f"DEFAULT_KEY_PREFIX: Final = {json.dumps(distributed_lock.key_prefix)}\n"
            f"DEFAULT_TTL_SECONDS: Final = {distributed_lock.ttl_seconds!r}\n"
            "\n"
            "\n"
            "class RedisMode(StrEnum):\n"
            "    STANDALONE = 'standalone'\n"
            "    SENTINEL = 'sentinel'\n"
            "    CLUSTER = 'cluster'\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class DistributedLockConfig:\n"
            f"    mode: RedisMode = RedisMode.{distributed_lock.mode.upper()}\n"
            "    redis_url: str = ''\n"
            "    cluster_startup_nodes: tuple[str, ...] = ()\n"
            "    sentinel_urls: str = ''\n"
            "    sentinel_master: str = DEFAULT_SENTINEL_MASTER\n"
            "    key_prefix: str = DEFAULT_KEY_PREFIX\n"
            "    ttl_seconds: int = DEFAULT_TTL_SECONDS\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> DistributedLockConfig:\n"
            "        mode = RedisMode(DEFAULT_MODE)\n"
            "        if mode is RedisMode.CLUSTER:\n"
            "            redis_url = _required_environment(REDIS_CLUSTER_URL_ENV)\n"
            "            startup_nodes = tuple(\n"
            "                value.strip()\n"
            "                for value in os.environ.get(REDIS_CLUSTER_STARTUP_NODES_ENV, '').split(',')\n"
            "                if value.strip()\n"
            "            )\n"
            "            return cls(\n"
            "                mode=mode,\n"
            "                redis_url=redis_url,\n"
            "                cluster_startup_nodes=startup_nodes,\n"
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
            "class DistributedLockClient(Protocol):\n"
            "    async def health_check(self) -> None: ...\n"
            "\n"
            "    async def acquire(\n"
            "        self, key: str, *, ttl_seconds: int | None = None\n"
            "    ) -> str | None: ...\n"
            "\n"
            "    async def release(self, key: str, token: str) -> bool: ...\n"
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
            "class FakeDistributedLockClient:\n"
            "    \"\"\"Deterministic lease fake with owner-only release semantics.\"\"\"\n"
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
            "        self._leases: dict[str, tuple[str, float]] = {}\n"
            "        self._next_token = 0\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        return None\n"
            "\n"
            "    async def acquire(\n"
            "        self, key: str, *, ttl_seconds: int | None = None\n"
            "    ) -> str | None:\n"
            "        self._require_key(key)\n"
            "        self._expire(key)\n"
            "        if key in self._leases:\n"
            "            return None\n"
            "        ttl = self._ttl(ttl_seconds)\n"
            "        self._next_token += 1\n"
            "        token = f'lock-token-{self._next_token}'\n"
            "        self._leases[key] = (token, self._clock() + ttl)\n"
            "        return token\n"
            "\n"
            "    async def release(self, key: str, token: str) -> bool:\n"
            "        self._require_key(key)\n"
            "        self._expire(key)\n"
            "        lease = self._leases.get(key)\n"
            "        if lease is None or lease[0] != token:\n"
            "            return False\n"
            "        del self._leases[key]\n"
            "        return True\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
            "\n"
            "    def _expire(self, key: str) -> None:\n"
            "        lease = self._leases.get(key)\n"
            "        if lease is not None and lease[1] <= self._clock():\n"
            "            del self._leases[key]\n"
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
            "            raise ValueError('lock key must not be empty')\n"
        )

    @staticmethod
    def _render_redis() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import secrets\n"
            "from urllib.parse import urlparse\n"
            "\n"
            "from redis.asyncio import Redis\n"
            "from redis.asyncio.cluster import RedisCluster\n"
            "from redis.asyncio.sentinel import Sentinel\n"
            "from redis.cluster import ClusterNode\n"
            "\n"
            "from .config import DistributedLockConfig, RedisMode\n"
            "\n"
            "_RELEASE_IF_OWNER = \"\"\"\n"
            "if redis.call('get', KEYS[1]) == ARGV[1] then\n"
            "    return redis.call('del', KEYS[1])\n"
            "end\n"
            "return 0\n"
            "\"\"\"\n"
            "\n"
            "\n"
            "class RedisDistributedLockClient:\n"
            "    def __init__(\n"
            "        self,\n"
            "        config: DistributedLockConfig,\n"
            "        *,\n"
            "        client: Redis | RedisCluster | None = None,\n"
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
            "                socket_timeout=2,\n"
            "                decode_responses=True,\n"
            "            )\n"
            "            self._client = self._sentinel.master_for(\n"
            "                config.sentinel_master,\n"
            "                socket_timeout=2,\n"
            "                decode_responses=True,\n"
            "            )\n"
            "            self._owns_client = True\n"
            "        else:\n"
            "            self._client = Redis.from_url(config.redis_url, decode_responses=True)\n"
            "            self._owns_client = True\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        if not await self._client.ping():\n"
            "            raise RuntimeError('Redis lock health check failed')\n"
            "\n"
            "    async def acquire(\n"
            "        self, key: str, *, ttl_seconds: int | None = None\n"
            "    ) -> str | None:\n"
            "        ttl = self._ttl(ttl_seconds)\n"
            "        token = secrets.token_urlsafe(32)\n"
            "        acquired = await self._client.set(\n"
            "            self._key(key), token, nx=True, ex=ttl\n"
            "        )\n"
            "        return token if acquired else None\n"
            "\n"
            "    async def release(self, key: str, token: str) -> bool:\n"
            "        released = await self._client.eval(\n"
            "            _RELEASE_IF_OWNER, 1, self._key(key), token\n"
            "        )\n"
            "        return bool(released)\n"
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
            "            raise ValueError('lock key must not be empty')\n"
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
            "from .config import DistributedLockConfig\n"
            "from .protocol import DistributedLockClient\n"
            "\n"
            "\n"
            "class DistributedLock:\n"
            "    def __init__(\n"
            "        self, client: DistributedLockClient, default_ttl_seconds: int\n"
            "    ) -> None:\n"
            "        self._client = client\n"
            "        self._default_ttl_seconds = default_ttl_seconds\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> DistributedLock:\n"
            "        from .redis import RedisDistributedLockClient\n"
            "\n"
            "        config = DistributedLockConfig.from_environment()\n"
            "        return cls(RedisDistributedLockClient(config), config.ttl_seconds)\n"
            "\n"
            "    async def health_check(self) -> None:\n"
            "        await self._client.health_check()\n"
            "\n"
            "    async def acquire(\n"
            "        self, key: str, *, ttl_seconds: int | None = None\n"
            "    ) -> str | None:\n"
            "        return await self._client.acquire(\n"
            "            key,\n"
            "            ttl_seconds=(\n"
            "                self._default_ttl_seconds\n"
            "                if ttl_seconds is None\n"
            "                else ttl_seconds\n"
            "            ),\n"
            "        )\n"
            "\n"
            "    async def release(self, key: str, token: str) -> bool:\n"
            "        return await self._client.release(key, token)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._client.aclose()\n"
        )
