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
from autoforge.core.specification import NotificationSpec, ProjectSpec

NOTIFICATION_GENERATOR_ID: Final = "autoforge.generator.service.notification"
NOTIFICATION_GENERATOR_VERSION: Final = "0.1.0"


class NotificationGenerator:
    """Generate an async outbound webhook notification boundary."""

    @property
    def generator_id(self) -> str:
        return NOTIFICATION_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return NOTIFICATION_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        notification = specification.tooling.notification
        if not notification.enabled:
            return {}

        root = PurePosixPath(
            "src", specification.project.package_name, "infrastructure", "notification"
        )
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(notification),
            root / "fake.py": self._render_fake(),
            root / "protocol.py": self._render_protocol(),
            root / "webhook.py": self._render_webhook(),
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
                    source=f"project:{specification.project.package_name}:notification",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .config import NotificationConfig\n"
            "from .fake import FakeNotificationDelivery\n"
            "from .protocol import Notification, NotificationDelivery, NotificationDeliveryError\n"
            "from .service import NotificationDispatcher\n"
            "from .webhook import WebhookNotificationDelivery\n"
            "\n"
            "__all__ = [\n"
            '    "FakeNotificationDelivery",\n'
            '    "Notification",\n'
            '    "NotificationConfig",\n'
            '    "NotificationDelivery",\n'
            '    "NotificationDeliveryError",\n'
            '    "NotificationDispatcher",\n'
            '    "WebhookNotificationDelivery",\n'
            "]\n"
        )

    @staticmethod
    def _render_config(notification: NotificationSpec) -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "from dataclasses import dataclass\n"
            "from typing import Final\n"
            "\n"
            f"NOTIFICATION_WEBHOOK_URL_ENV: Final = {json.dumps(notification.webhook_url_environment)}\n"
            f"DEFAULT_TIMEOUT_SECONDS: Final = {notification.timeout_seconds!r}\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class NotificationConfig:\n"
            "    webhook_url: str\n"
            "    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> NotificationConfig:\n"
            "        webhook_url = os.environ.get(NOTIFICATION_WEBHOOK_URL_ENV)\n"
            "        if not webhook_url:\n"
            "            raise RuntimeError(f'{NOTIFICATION_WEBHOOK_URL_ENV} must be set')\n"
            "        return cls(webhook_url=webhook_url)\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from dataclasses import dataclass, field\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class Notification:\n"
            "    subject: str\n"
            "    body: str\n"
            "    attributes: dict[str, object] = field(default_factory=dict)\n"
            "\n"
            "    def as_payload(self) -> dict[str, object]:\n"
            "        return {\n"
            "            'subject': self.subject,\n"
            "            'body': self.body,\n"
            "            'attributes': self.attributes,\n"
            "        }\n"
            "\n"
            "\n"
            "class NotificationDelivery(Protocol):\n"
            "    async def send(self, notification: Notification) -> None: ...\n"
            "\n"
            "    async def aclose(self) -> None: ...\n"
            "\n"
            "\n"
            "class NotificationDeliveryError(RuntimeError):\n"
            "    pass\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from .protocol import Notification\n"
            "\n"
            "\n"
            "class FakeNotificationDelivery:\n"
            "    \"\"\"Deterministic delivery fake for application tests.\"\"\"\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self.notifications: list[Notification] = []\n"
            "\n"
            "    async def send(self, notification: Notification) -> None:\n"
            "        self.notifications.append(notification)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        return None\n"
        )

    @staticmethod
    def _render_webhook() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "import httpx\n"
            "\n"
            "from .config import NotificationConfig\n"
            "from .protocol import Notification, NotificationDeliveryError\n"
            "\n"
            "\n"
            "class WebhookNotificationDelivery:\n"
            "    def __init__(\n"
            "        self, config: NotificationConfig, *, client: httpx.AsyncClient | None = None\n"
            "    ) -> None:\n"
            "        self._client = client or httpx.AsyncClient(timeout=config.timeout_seconds)\n"
            "        self._webhook_url = config.webhook_url\n"
            "        self._owns_client = client is None\n"
            "\n"
            "    async def send(self, notification: Notification) -> None:\n"
            "        response = await self._client.post(self._webhook_url, json=notification.as_payload())\n"
            "        if not 200 <= response.status_code < 300:\n"
            "            raise NotificationDeliveryError(\n"
            "                f'notification webhook returned {response.status_code}'\n"
            "            )\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        if self._owns_client:\n"
            "            await self._client.aclose()\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n"
            "\n"
            "from .config import NotificationConfig\n"
            "from .protocol import Notification, NotificationDelivery\n"
            "\n"
            "\n"
            "class NotificationDispatcher:\n"
            "    def __init__(self, delivery: NotificationDelivery) -> None:\n"
            "        self._delivery = delivery\n"
            "\n"
            "    @classmethod\n"
            "    def from_environment(cls) -> NotificationDispatcher:\n"
            "        from .webhook import WebhookNotificationDelivery\n"
            "\n"
            "        return cls(WebhookNotificationDelivery(NotificationConfig.from_environment()))\n"
            "\n"
            "    async def send(self, notification: Notification) -> None:\n"
            "        await self._delivery.send(notification)\n"
            "\n"
            "    async def aclose(self) -> None:\n"
            "        await self._delivery.aclose()\n"
        )
