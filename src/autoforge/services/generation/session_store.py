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
from autoforge.core.specification import ProjectSpec, ServiceSpec

SESSION_STORE_GENERATOR_ID: Final = "autoforge.generator.service.session_store"
SESSION_STORE_GENERATOR_VERSION: Final = "0.1.0"


class SessionStoreGenerator:
    """Redis-backed SessionStore contract, fake and adapter generator."""

    @property
    def generator_id(self) -> str:
        return SESSION_STORE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return SESSION_STORE_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        services = self._session_services(specification)
        if not services:
            return {}
        if len(services) != 1:
            raise ValueError("redis_session Service는 Application에 하나만 허용됩니다.")

        service = services[0]
        root = PurePosixPath(
            "src",
            specification.project.package_name,
            "infrastructure",
            "session_store",
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "protocol.py": self._render_protocol(),
            root / "fake.py": self._render_fake(),
            root / "redis.py": self._render_redis(service),
            root / "provider.py": self._render_provider(service),
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
                        f"project:{specification.project.package_name}:"
                        "session-store"
                    ),
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _session_services(specification: ProjectSpec) -> list[ServiceSpec]:
        return [
            service
            for service in specification.application.services
            if service.kind == "redis_session"
        ]

    @staticmethod
    def _render_init() -> str:
        return (
            "from .fake import FakeSessionStore\n"
            "from .protocol import SessionData, SessionStore, SessionStoreError\n"
            "\n"
            "__all__ = [\n"
            '    "FakeSessionStore",\n'
            '    "SessionData",\n'
            '    "SessionStore",\n'
            '    "SessionStoreError",\n'
            "]\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from dataclasses import dataclass\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class SessionStoreError(RuntimeError):\n"
            "    pass\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class SessionData:\n"
            "    session_id: str\n"
            "    user_id: str\n"
            "    data: dict[str, object]\n"
            "\n"
            "\n"
            "class SessionStore(Protocol):\n"
            "    async def create(self, session: SessionData) -> None: ...\n"
            "\n"
            "    async def get(self, session_id: str) -> SessionData | None: ...\n"
            "\n"
            "    async def refresh(self, session_id: str) -> bool: ...\n"
            "\n"
            "    async def revoke(self, session_id: str) -> bool: ...\n"
            "\n"
            "    async def revoke_user_sessions(self, user_id: str) -> int: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from collections.abc import Callable\n"
            "from time import monotonic\n"
            "\n"
            "from .protocol import SessionData\n"
            "\n"
            "\n"
            "class FakeSessionStore:\n"
            "    def __init__(\n"
            "        self, ttl_seconds: int, clock: Callable[[], float] = monotonic,\n"
            "    ) -> None:\n"
            "        if ttl_seconds <= 0:\n"
            '            raise ValueError("ttl_seconds must be positive")\n'
            "        self._ttl_seconds = ttl_seconds\n"
            "        self._clock = clock\n"
            "        self._sessions: dict[str, tuple[SessionData, float]] = {}\n"
            "        self._user_sessions: dict[str, set[str]] = {}\n"
            "\n"
            "    async def create(self, session: SessionData) -> None:\n"
            "        await self.revoke(session.session_id)\n"
            "        expires_at = self._clock() + self._ttl_seconds\n"
            "        self._sessions[session.session_id] = (session, expires_at)\n"
            "        self._user_sessions.setdefault(session.user_id, set()).add(\n"
            "            session.session_id\n"
            "        )\n"
            "\n"
            "    async def get(self, session_id: str) -> SessionData | None:\n"
            "        stored = self._sessions.get(session_id)\n"
            "        if stored is None:\n"
            "            return None\n"
            "        session, expires_at = stored\n"
            "        if expires_at <= self._clock():\n"
            "            await self.revoke(session_id)\n"
            "            return None\n"
            "        return session\n"
            "\n"
            "    async def refresh(self, session_id: str) -> bool:\n"
            "        session = await self.get(session_id)\n"
            "        if session is None:\n"
            "            return False\n"
            "        self._sessions[session_id] = (\n"
            "            session, self._clock() + self._ttl_seconds\n"
            "        )\n"
            "        return True\n"
            "\n"
            "    async def revoke(self, session_id: str) -> bool:\n"
            "        stored = self._sessions.pop(session_id, None)\n"
            "        if stored is None:\n"
            "            return False\n"
            "        session, _ = stored\n"
            "        user_sessions = self._user_sessions.get(session.user_id)\n"
            "        if user_sessions is not None:\n"
            "            user_sessions.discard(session_id)\n"
            "            if not user_sessions:\n"
            "                self._user_sessions.pop(session.user_id, None)\n"
            "        return True\n"
            "\n"
            "    async def revoke_user_sessions(self, user_id: str) -> int:\n"
            "        session_ids = tuple(self._user_sessions.get(user_id, set()))\n"
            "        for session_id in session_ids:\n"
            "            await self.revoke(session_id)\n"
            "        return len(session_ids)\n"
        )

    @staticmethod
    def _render_redis(service: ServiceSpec) -> str:
        namespace = json.dumps(service.namespace)
        return (
            "import json\n"
            "\n"
            "from redis.asyncio import Redis\n"
            "from redis.exceptions import RedisError\n"
            "\n"
            "from .protocol import SessionData, SessionStoreError\n"
            "\n"
            "\n"
            "class RedisSessionStore:\n"
            f"    _namespace = {namespace}\n"
            f"    _ttl_seconds = {service.ttl_seconds}\n"
            "\n"
            "    def __init__(self, client: Redis) -> None:\n"
            "        self._client = client\n"
            "\n"
            "    async def create(self, session: SessionData) -> None:\n"
            "        payload = json.dumps(\n"
            "            {\"user_id\": session.user_id, \"data\": session.data},\n"
            "            separators=(\",\", \":\"),\n"
            "            sort_keys=True,\n"
            "        )\n"
            "        try:\n"
            "            async with self._client.pipeline(transaction=True) as pipe:\n"
            "                pipe.set(\n"
            "                    self._session_key(session.session_id),\n"
            "                    payload,\n"
            "                    ex=self._ttl_seconds,\n"
            "                )\n"
            "                pipe.sadd(self._user_key(session.user_id), session.session_id)\n"
            "                pipe.expire(self._user_key(session.user_id), self._ttl_seconds)\n"
            "                await pipe.execute()\n"
            "        except RedisError as error:\n"
            '            raise SessionStoreError("Redis session create failed") from error\n'
            "\n"
            "    async def get(self, session_id: str) -> SessionData | None:\n"
            "        try:\n"
            "            payload = await self._client.get(self._session_key(session_id))\n"
            "        except RedisError as error:\n"
            '            raise SessionStoreError("Redis session get failed") from error\n'
            "        if payload is None:\n"
            "            return None\n"
            "        if isinstance(payload, bytes):\n"
            "            payload = payload.decode(\"utf-8\")\n"
            "        decoded = json.loads(payload)\n"
            "        return SessionData(\n"
            "            session_id=session_id,\n"
            "            user_id=decoded[\"user_id\"],\n"
            "            data=decoded[\"data\"],\n"
            "        )\n"
            "\n"
            "    async def refresh(self, session_id: str) -> bool:\n"
            "        session = await self.get(session_id)\n"
            "        if session is None:\n"
            "            return False\n"
            "        try:\n"
            "            async with self._client.pipeline(transaction=True) as pipe:\n"
            "                pipe.expire(self._session_key(session_id), self._ttl_seconds)\n"
            "                pipe.expire(self._user_key(session.user_id), self._ttl_seconds)\n"
            "                results = await pipe.execute()\n"
            "            return bool(results[0])\n"
            "        except RedisError as error:\n"
            '            raise SessionStoreError("Redis session refresh failed") from error\n'
            "\n"
            "    async def revoke(self, session_id: str) -> bool:\n"
            "        session = await self.get(session_id)\n"
            "        if session is None:\n"
            "            return False\n"
            "        try:\n"
            "            async with self._client.pipeline(transaction=True) as pipe:\n"
            "                pipe.delete(self._session_key(session_id))\n"
            "                pipe.srem(self._user_key(session.user_id), session_id)\n"
            "                results = await pipe.execute()\n"
            "            return bool(results[0])\n"
            "        except RedisError as error:\n"
            '            raise SessionStoreError("Redis session revoke failed") from error\n'
            "\n"
            "    async def revoke_user_sessions(self, user_id: str) -> int:\n"
            "        user_key = self._user_key(user_id)\n"
            "        try:\n"
            "            session_ids = await self._client.smembers(user_key)\n"
            "            normalized = [\n"
            "                value.decode(\"utf-8\") if isinstance(value, bytes) else value\n"
            "                for value in session_ids\n"
            "            ]\n"
            "            if not normalized:\n"
            "                return 0\n"
            "            keys = [self._session_key(value) for value in normalized]\n"
            "            await self._client.delete(*keys, user_key)\n"
            "            return len(normalized)\n"
            "        except RedisError as error:\n"
            '            raise SessionStoreError("Redis user session revoke failed") from error\n'
            "\n"
            "    def _session_key(self, session_id: str) -> str:\n"
            '        return f"{self._namespace}:session:{session_id}"\n'
            "\n"
            "    def _user_key(self, user_id: str) -> str:\n"
            '        return f"{self._namespace}:user-sessions:{user_id}"\n'
        )

    @staticmethod
    def _render_provider(service: ServiceSpec) -> str:
        if service.mode == "sentinel":
            return SessionStoreGenerator._render_sentinel_provider(service)
        url_env = json.dumps(service.url_env)
        return (
            "import os\n"
            "from collections.abc import AsyncIterator\n"
            "from contextlib import asynccontextmanager\n"
            "from typing import Annotated\n"
            "\n"
            "from fastapi import Depends, FastAPI, HTTPException, Request, status\n"
            "from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer\n"
            "from redis.asyncio import Redis\n"
            "\n"
            "from .protocol import SessionData, SessionStore, SessionStoreError\n"
            "from .redis import RedisSessionStore\n"
            "\n"
            f"REDIS_URL_ENV = {url_env}\n"
            "\n"
            "\n"
            "@asynccontextmanager\n"
            "async def session_store_lifespan(\n"
            "    app: FastAPI,\n"
            ") -> AsyncIterator[None]:\n"
            "    redis_url = os.environ.get(REDIS_URL_ENV)\n"
            "    if not redis_url:\n"
            "        raise SessionStoreError(\n"
            '            f"Required environment variable is missing: {REDIS_URL_ENV}"\n'
            "        )\n"
            "    client = Redis.from_url(redis_url, decode_responses=True)\n"
            "    app.state.session_store = RedisSessionStore(client)\n"
            "    try:\n"
            "        yield\n"
            "    finally:\n"
            "        del app.state.session_store\n"
            "        await client.aclose()\n"
            "\n"
            "\n"
            "def get_session_store(request: Request) -> SessionStore:\n"
            "    try:\n"
            "        return request.app.state.session_store\n"
            "    except AttributeError as error:\n"
            "        raise SessionStoreError(\n"
            '            "SessionStore is not initialized"\n'
            "        ) from error\n"
            "\n"
            "\n"
            "bearer_scheme = HTTPBearer(auto_error=False)\n"
            "\n"
            "\n"
            "async def get_current_session(\n"
            "    credentials: Annotated[\n"
            "        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)\n"
            "    ],\n"
            "    session_store: Annotated[SessionStore, Depends(get_session_store)],\n"
            ") -> SessionData:\n"
            "    if credentials is None:\n"
            "        raise HTTPException(\n"
            "            status_code=status.HTTP_401_UNAUTHORIZED,\n"
            '            detail="Bearer session is required",\n'
            "        )\n"
            "    session = await session_store.get(credentials.credentials)\n"
            "    if session is None:\n"
            "        raise HTTPException(\n"
            "            status_code=status.HTTP_401_UNAUTHORIZED,\n"
            '            detail="Invalid session",\n'
            "        )\n"
            "    return session\n"
        )

    @staticmethod
    def _render_sentinel_provider(service: ServiceSpec) -> str:
        sentinel_urls_env = json.dumps(service.sentinel_urls_env)
        master_name = json.dumps(service.sentinel_master)
        return (
            "import os\n"
            "from collections.abc import AsyncIterator\n"
            "from contextlib import asynccontextmanager\n"
            "from typing import Annotated\n"
            "\n"
            "from fastapi import Depends, FastAPI, HTTPException, Request, status\n"
            "from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer\n"
            "from redis.asyncio.sentinel import Sentinel\n"
            "\n"
            "from .protocol import SessionData, SessionStore, SessionStoreError\n"
            "from .redis import RedisSessionStore\n"
            "\n"
            f"REDIS_SENTINEL_URLS_ENV = {sentinel_urls_env}\n"
            f"REDIS_SENTINEL_MASTER = {master_name}\n"
            "\n"
            "\n"
            "def _sentinel_endpoints(value: str) -> list[tuple[str, int]]:\n"
            "    endpoints: list[tuple[str, int]] = []\n"
            "    for item in value.split(','):\n"
            "        host, separator, port_text = item.strip().rpartition(':')\n"
            "        if not separator or not host:\n"
            "            raise SessionStoreError(\n"
            '                f"Invalid Redis Sentinel endpoint: {item!r}"\n'
            "            )\n"
            "        try:\n"
            "            port = int(port_text)\n"
            "        except ValueError as error:\n"
            "            raise SessionStoreError(\n"
            '                f"Invalid Redis Sentinel port: {item!r}"\n'
            "            ) from error\n"
            "        endpoints.append((host, port))\n"
            "    if not endpoints:\n"
            '        raise SessionStoreError("Redis Sentinel endpoints are empty")\n'
            "    return endpoints\n"
            "\n"
            "\n"
            "@asynccontextmanager\n"
            "async def session_store_lifespan(\n"
            "    app: FastAPI,\n"
            ") -> AsyncIterator[None]:\n"
            "    raw_urls = os.environ.get(REDIS_SENTINEL_URLS_ENV)\n"
            "    if not raw_urls:\n"
            "        raise SessionStoreError(\n"
            "            f\"Required environment variable is missing: \"\n"
            "            f\"{REDIS_SENTINEL_URLS_ENV}\"\n"
            "        )\n"
            "    sentinel = Sentinel(\n"
            "        _sentinel_endpoints(raw_urls),\n"
            "        socket_timeout=2,\n"
            "        decode_responses=True,\n"
            "    )\n"
            "    client = sentinel.master_for(\n"
            "        REDIS_SENTINEL_MASTER,\n"
            "        socket_timeout=2,\n"
            "        decode_responses=True,\n"
            "    )\n"
            "    app.state.session_store = RedisSessionStore(client)\n"
            "    try:\n"
            "        yield\n"
            "    finally:\n"
            "        del app.state.session_store\n"
            "        await client.aclose()\n"
            "        for sentinel_client in sentinel.sentinels:\n"
            "            await sentinel_client.aclose()\n"
            "\n"
            "\n"
            "def get_session_store(request: Request) -> SessionStore:\n"
            "    try:\n"
            "        return request.app.state.session_store\n"
            "    except AttributeError as error:\n"
            "        raise SessionStoreError(\n"
            '            "SessionStore is not initialized"\n'
            "        ) from error\n"
            "\n"
            "\n"
            "bearer_scheme = HTTPBearer(auto_error=False)\n"
            "\n"
            "\n"
            "async def get_current_session(\n"
            "    credentials: Annotated[\n"
            "        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)\n"
            "    ],\n"
            "    session_store: Annotated[SessionStore, Depends(get_session_store)],\n"
            ") -> SessionData:\n"
            "    if credentials is None:\n"
            "        raise HTTPException(\n"
            "            status_code=status.HTTP_401_UNAUTHORIZED,\n"
            '            detail="Bearer session is required",\n'
            "        )\n"
            "    session = await session_store.get(credentials.credentials)\n"
            "    if session is None:\n"
            "        raise HTTPException(\n"
            "            status_code=status.HTTP_401_UNAUTHORIZED,\n"
            '            detail="Invalid session",\n'
            "        )\n"
            "    return session\n"
        )
