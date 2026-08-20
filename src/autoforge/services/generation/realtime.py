import json
from pathlib import PurePosixPath
from textwrap import dedent
from typing import Final

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import ProjectSpec, RealtimeSpec, ServiceSpec

REALTIME_GENERATOR_ID: Final = "autoforge.generator.service.realtime"
REALTIME_GENERATOR_VERSION: Final = "0.1.0"


class RealtimeGenerator:
    """Generate an async local realtime hub and optional Redis hint backplane."""

    @property
    def generator_id(self) -> str:
        return REALTIME_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return REALTIME_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        realtime = specification.tooling.realtime
        if not realtime.enabled:
            return {}

        root = PurePosixPath(
            "src", specification.project.package_name, "infrastructure", "realtime"
        )
        has_redis_backplane = realtime.backplane == "redis_pubsub"
        rendered = {
            root / "__init__.py": self._render_init(has_redis_backplane),
            root / "fake.py": self._render_fake(has_redis_backplane),
            root / "protocol.py": self._render_protocol(has_redis_backplane),
            root / "service.py": self._render_service(),
            root / "websocket.py": self._render_websocket(),
        }
        if has_redis_backplane:
            rendered[root / "backplane.py"] = self._render_backplane(
                self._redis_service(specification), realtime
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
                    source=f"project:{specification.project.package_name}:realtime",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _redis_service(specification: ProjectSpec) -> ServiceSpec:
        return next(
            service
            for service in specification.application.services
            if service.kind == "redis_session"
        )

    @staticmethod
    def _render_init(has_redis_backplane: bool) -> str:
        imports = (
            "from .fake import FakeRealtimeSubscriber\n"
            "from .protocol import RealtimeSubscriber\n"
            "from .service import RealtimeHub\n"
            "from .websocket import FastAPIWebSocketSubscriber\n"
        )
        exports = [
            "FakeRealtimeSubscriber",
            "FastAPIWebSocketSubscriber",
            "RealtimeHub",
            "RealtimeSubscriber",
        ]
        if has_redis_backplane:
            imports += (
                "from .backplane import (\n"
                "    RedisPubSubRealtimeBackplane,\n"
                "    RealtimeBackplaneError,\n"
                ")\n"
                "from .fake import FakeRealtimeBackplane\n"
                "from .protocol import RealtimeBackplane\n"
            )
            exports.extend(
                [
                    "FakeRealtimeBackplane",
                    "RealtimeBackplane",
                    "RealtimeBackplaneError",
                    "RedisPubSubRealtimeBackplane",
                ]
            )
        return imports + "\n__all__ = [\n" + "".join(
            f'    "{export}",\n' for export in sorted(exports)
        ) + "]\n"

    @staticmethod
    def _render_protocol(has_redis_backplane: bool) -> str:
        source = (
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class RealtimeSubscriber(Protocol):\n"
            "    async def send(self, message: str) -> None: ...\n"
        )
        if not has_redis_backplane:
            return source
        return (
            "from collections.abc import Awaitable, Callable\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "RealtimeDeliveryHandler = Callable[[str, str], Awaitable[None]]\n"
            "\n"
            "\n"
            "class RealtimeSubscriber(Protocol):\n"
            "    async def send(self, message: str) -> None: ...\n"
            "\n"
            "\n"
            "class RealtimeBackplane(Protocol):\n"
            "    async def start(self, deliver: RealtimeDeliveryHandler) -> None: ...\n"
            "\n"
            "    async def publish(self, channel: str, message: str) -> None: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake(has_redis_backplane: bool) -> str:
        source = (
            "from dataclasses import dataclass, field\n"
            "\n"
            "\n"
            "@dataclass\n"
            "class FakeRealtimeSubscriber:\n"
            "    \"\"\"Deterministic subscriber fake for application tests.\"\"\"\n"
            "\n"
            "    messages: list[str] = field(default_factory=list)\n"
            "\n"
            "    async def send(self, message: str) -> None:\n"
            "        self.messages.append(message)\n"
        )
        if not has_redis_backplane:
            return source
        return (
            "from dataclasses import dataclass, field\n"
            "\n"
            "from .protocol import RealtimeDeliveryHandler\n"
            "\n"
            "\n"
            "@dataclass\n"
            "class FakeRealtimeSubscriber:\n"
            "    \"\"\"Deterministic subscriber fake for application tests.\"\"\"\n"
            "\n"
            "    messages: list[str] = field(default_factory=list)\n"
            "\n"
            "    async def send(self, message: str) -> None:\n"
            "        self.messages.append(message)\n"
            "\n"
            "\n"
            "class FakeRealtimeBackplane:\n"
            "    \"\"\"Deterministic in-memory stand-in for Redis Pub/Sub hints.\"\"\"\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self.published: list[tuple[str, str]] = []\n"
            "        self._deliver: RealtimeDeliveryHandler | None = None\n"
            "        self._closed = False\n"
            "\n"
            "    async def start(self, deliver: RealtimeDeliveryHandler) -> None:\n"
            "        if self._closed:\n"
            "            raise RuntimeError('realtime backplane is closed')\n"
            "        self._deliver = deliver\n"
            "\n"
            "    async def publish(self, channel: str, message: str) -> None:\n"
            "        if self._closed:\n"
            "            raise RuntimeError('realtime backplane is closed')\n"
            "        self.published.append((channel, message))\n"
            "        if self._deliver is not None:\n"
            "            await self._deliver(channel, message)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        self._closed = True\n"
            "        self._deliver = None\n"
        )

    @staticmethod
    def _render_backplane(service: ServiceSpec, realtime: RealtimeSpec) -> str:
        if service.mode == "cluster":
            environment = (
                "REDIS_CLUSTER_URL_ENV = "
                f"{json.dumps(service.cluster_url_env)}\n"
                "REDIS_CLUSTER_STARTUP_NODES_ENV = "
                f"{json.dumps(service.cluster_startup_nodes_env)}"
            )
            url_loader = """\
def _redis_urls_from_environment() -> tuple[str, ...]:
    values = [
        value.strip()
        for value in os.environ.get(REDIS_CLUSTER_STARTUP_NODES_ENV, "").split(",")
        if value.strip()
    ]
    cluster_url = os.environ.get(REDIS_CLUSTER_URL_ENV)
    if cluster_url and cluster_url not in values:
        values.insert(0, cluster_url)
    if not values:
        raise RealtimeBackplaneError(
            "Redis Cluster realtime backplane requires at least one startup node"
        )
    return tuple(values)
"""
        else:
            environment = f"REDIS_URL_ENV = {json.dumps(service.url_env)}"
            url_loader = """\
def _redis_urls_from_environment() -> tuple[str, ...]:
    redis_url = os.environ.get(REDIS_URL_ENV)
    if not redis_url:
        raise RealtimeBackplaneError(
            f"Required environment variable is missing: {REDIS_URL_ENV}"
        )
    return (redis_url,)
"""
        return dedent(
            """\
            from __future__ import annotations

            import asyncio
            import json
            import os
            from contextlib import suppress

            from redis.asyncio import Redis
            from redis.exceptions import RedisError

            from .protocol import RealtimeDeliveryHandler

            REALTIME_TOPIC = __TOPIC__
            RECONNECT_DELAY_SECONDS = __RECONNECT_DELAY__
            __ENVIRONMENT__


            class RealtimeBackplaneError(RuntimeError):
                pass


            class RedisPubSubRealtimeBackplane:
                \"\"\"Best-effort multi-replica hint transport over Redis Pub/Sub.\"\"\"

                def __init__(
                    self,
                    urls: tuple[str, ...],
                    *,
                    topic: str = REALTIME_TOPIC,
                    reconnect_delay_seconds: float = RECONNECT_DELAY_SECONDS,
                ) -> None:
                    if not urls:
                        raise ValueError(
                            \"Redis realtime backplane requires at least one URL\"
                        )
                    if not topic:
                        raise ValueError(\"Redis realtime topic must not be empty\")
                    self._urls = urls
                    self._topic = topic
                    self._reconnect_delay_seconds = reconnect_delay_seconds
                    self._publisher: Redis | None = None
                    self._listener: asyncio.Task[None] | None = None
                    self._closed = False

                @classmethod
                def from_environment(cls) -> RedisPubSubRealtimeBackplane:
                    return cls(_redis_urls_from_environment())

                async def start(self, deliver: RealtimeDeliveryHandler) -> None:
                    if self._closed:
                        raise RealtimeBackplaneError(\"realtime backplane is closed\")
                    if self._listener is not None:
                        raise RealtimeBackplaneError(
                            \"realtime backplane is already started\"
                        )
                    self._listener = asyncio.create_task(self._listen(deliver))

                async def publish(self, channel: str, message: str) -> None:
                    if self._closed:
                        raise RealtimeBackplaneError(\"realtime backplane is closed\")
                    if not channel:
                        raise ValueError(\"realtime channel must not be empty\")
                    payload = json.dumps(dict(channel=channel, message=message))
                    for _ in range(2):
                        client = await self._publisher_client()
                        try:
                            await client.publish(self._topic, payload)
                            return
                        except RedisError:
                            await self._discard_publisher()
                    raise RealtimeBackplaneError(\"Redis realtime publish failed\")

                async def aclose(self) -> None:
                    self._closed = True
                    listener = self._listener
                    self._listener = None
                    if listener is not None:
                        listener.cancel()
                        with suppress(asyncio.CancelledError):
                            await listener
                    await self._discard_publisher()

                async def _publisher_client(self) -> Redis:
                    if self._publisher is None:
                        self._publisher = await self._open_client()
                    return self._publisher

                async def _discard_publisher(self) -> None:
                    publisher = self._publisher
                    self._publisher = None
                    if publisher is not None:
                        await publisher.aclose()

                async def _listen(self, deliver: RealtimeDeliveryHandler) -> None:
                    while not self._closed:
                        client: Redis | None = None
                        pubsub = None
                        try:
                            client = await self._open_client()
                            pubsub = client.pubsub()
                            await pubsub.subscribe(self._topic)
                            while not self._closed:
                                event = await pubsub.get_message(
                                    ignore_subscribe_messages=True, timeout=1.0
                                )
                                if event is None:
                                    continue
                                payload = _decode_payload(event.get(\"data\"))
                                if payload is not None:
                                    await deliver(*payload)
                        except (RedisError, RealtimeBackplaneError):
                            pass
                        finally:
                            if pubsub is not None:
                                await pubsub.aclose()
                            if client is not None:
                                await client.aclose()
                        if not self._closed:
                            await asyncio.sleep(self._reconnect_delay_seconds)

                async def _open_client(self) -> Redis:
                    last_error: RedisError | None = None
                    for url in self._urls:
                        client = Redis.from_url(url, decode_responses=True)
                        try:
                            await client.ping()
                            return client
                        except RedisError as error:
                            last_error = error
                            await client.aclose()
                    raise RealtimeBackplaneError(
                        \"Redis realtime connection failed\"
                    ) from last_error


            __URL_LOADER__


            def _decode_payload(value: object) -> tuple[str, str] | None:
                if not isinstance(value, str):
                    return None
                try:
                    payload = json.loads(value)
                except json.JSONDecodeError:
                    return None
                channel = payload.get(\"channel\") if isinstance(payload, dict) else None
                message = payload.get(\"message\") if isinstance(payload, dict) else None
                if not isinstance(channel, str) or not channel:
                    return None
                if not isinstance(message, str):
                    return None
                return channel, message
            """
        ).replace("__TOPIC__", json.dumps(realtime.channel)).replace(
            "__RECONNECT_DELAY__", json.dumps(realtime.reconnect_delay_seconds)
        ).replace("__ENVIRONMENT__", environment).replace(
            "__URL_LOADER__", url_loader
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import asyncio\n"
            "\n"
            "from .protocol import RealtimeSubscriber\n"
            "\n"
            "\n"
            "class RealtimeHub:\n"
            "    \"\"\"In-process channel fan-out; transport and policy stay consumer-owned.\"\"\"\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self._subscribers: dict[str, list[RealtimeSubscriber]] = {}\n"
            "        self._lock = asyncio.Lock()\n"
            "        self._closed = False\n"
            "\n"
            "    async def subscribe(self, channel: str, subscriber: RealtimeSubscriber) -> None:\n"
            "        _require_channel(channel)\n"
            "        async with self._lock:\n"
            "            self._require_open()\n"
            "            subscribers = self._subscribers.setdefault(channel, [])\n"
            "            if not any(existing is subscriber for existing in subscribers):\n"
            "                subscribers.append(subscriber)\n"
            "\n"
            "    async def unsubscribe(self, channel: str, subscriber: RealtimeSubscriber) -> None:\n"
            "        _require_channel(channel)\n"
            "        async with self._lock:\n"
            "            subscribers = self._subscribers.get(channel)\n"
            "            if subscribers is None:\n"
            "                return\n"
            "            remaining = [item for item in subscribers if item is not subscriber]\n"
            "            if remaining:\n"
            "                self._subscribers[channel] = remaining\n"
            "            else:\n"
            "                self._subscribers.pop(channel, None)\n"
            "\n"
            "    async def publish(self, channel: str, message: str) -> int:\n"
            "        _require_channel(channel)\n"
            "        async with self._lock:\n"
            "            self._require_open()\n"
            "            subscribers = tuple(self._subscribers.get(channel, ()))\n"
            "        await asyncio.gather(*(subscriber.send(message) for subscriber in subscribers))\n"
            "        return len(subscribers)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        async with self._lock:\n"
            "            self._closed = True\n"
            "            self._subscribers.clear()\n"
            "\n"
            "    def _require_open(self) -> None:\n"
            "        if self._closed:\n"
            "            raise RuntimeError('realtime hub is closed')\n"
            "\n"
            "\n"
            "def _require_channel(channel: str) -> None:\n"
            "    if not channel.strip():\n"
            "        raise ValueError('realtime channel must not be empty')\n"
        )

    @staticmethod
    def _render_websocket() -> str:
        return (
            "from fastapi import WebSocket\n"
            "\n"
            "\n"
            "class FastAPIWebSocketSubscriber:\n"
            "    \"\"\"Adapt one accepted FastAPI WebSocket for RealtimeHub delivery.\"\"\"\n"
            "\n"
            "    def __init__(self, websocket: WebSocket) -> None:\n"
            "        self._websocket = websocket\n"
            "\n"
            "    async def send(self, message: str) -> None:\n"
            "        await self._websocket.send_text(message)\n"
        )
