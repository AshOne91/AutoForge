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
from autoforge.core.specification import ProjectSpec

REALTIME_GENERATOR_ID: Final = "autoforge.generator.service.realtime"
REALTIME_GENERATOR_VERSION: Final = "0.1.0"


class RealtimeGenerator:
    """Generate an async in-process realtime delivery boundary."""

    @property
    def generator_id(self) -> str:
        return REALTIME_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return REALTIME_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        if not specification.tooling.realtime.enabled:
            return {}

        root = PurePosixPath(
            "src", specification.project.package_name, "infrastructure", "realtime"
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "fake.py": self._render_fake(),
            root / "protocol.py": self._render_protocol(),
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
                    source=f"project:{specification.project.package_name}:realtime",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .fake import FakeRealtimeSubscriber\n"
            "from .protocol import RealtimeSubscriber\n"
            "from .service import RealtimeHub\n"
            "\n"
            "__all__ = [\n"
            '    "FakeRealtimeSubscriber",\n'
            '    "RealtimeHub",\n'
            '    "RealtimeSubscriber",\n'
            "]\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class RealtimeSubscriber(Protocol):\n"
            "    async def send(self, message: str) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
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
