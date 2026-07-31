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
