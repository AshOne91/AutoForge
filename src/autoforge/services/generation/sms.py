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
from autoforge.core.specification import ProjectSpec, SmsSpec

SMS_GENERATOR_ID: Final = "autoforge.generator.service.sms"
SMS_GENERATOR_VERSION: Final = "0.1.0"


class SmsGenerator:
    """Generate an async SMS contract with a SOLAPI adapter and fake."""

    @property
    def generator_id(self) -> str:
        return SMS_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return SMS_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        sms = specification.tooling.sms
        if not sms.enabled:
            return {}
        root = PurePosixPath("src", specification.project.package_name, "infrastructure", "sms")
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(sms),
            root / "fake.py": self._render_fake(),
            root / "protocol.py": self._render_protocol(),
            root / "service.py": self._render_service(),
            root / "solapi.py": self._render_solapi(),
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
                    source=f"project:{specification.project.package_name}:sms",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .config import SmsConfig\nfrom .fake import FakeSmsDelivery\n"
            "from .protocol import SmsDelivery, SmsMessage, SmsReceipt\n"
            "from .service import SmsSender\nfrom .solapi import SolapiSmsDelivery\n\n"
            "__all__ = [\n    \"FakeSmsDelivery\",\n    \"SmsConfig\",\n"
            "    \"SmsDelivery\",\n    \"SmsMessage\",\n    \"SmsReceipt\",\n"
            "    \"SmsSender\",\n    \"SolapiSmsDelivery\",\n]\n"
        )

    @staticmethod
    def _render_config(sms: SmsSpec) -> str:
        return (
            "from __future__ import annotations\n\nimport os\nfrom dataclasses import dataclass\n"
            "from typing import Final\n\n"
            f"API_KEY_ENV: Final = {json.dumps(sms.api_key_environment)}\n"
            f"API_SECRET_ENV: Final = {json.dumps(sms.api_secret_environment)}\n"
            f"SENDER_ENV: Final = {json.dumps(sms.sender_environment)}\n"
            f"DEFAULT_TIMEOUT_SECONDS: Final = {sms.timeout_seconds!r}\n\n"
            "@dataclass(frozen=True, slots=True)\nclass SmsConfig:\n"
            "    api_key: str\n    api_secret: str\n    sender: str\n"
            "    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n\n"
            "    @classmethod\n    def from_environment(cls) -> SmsConfig:\n"
            "        values = {name: os.environ.get(name) for name in (API_KEY_ENV, API_SECRET_ENV, SENDER_ENV)}\n"
            "        if any(not value for value in values.values()):\n            raise RuntimeError('SOLAPI credentials and sender must be set')\n"
            "        return cls(values[API_KEY_ENV], values[API_SECRET_ENV], values[SENDER_ENV])\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom typing import Protocol\n\n"
            "@dataclass(frozen=True, slots=True)\nclass SmsMessage:\n"
            "    to: str\n    text: str\n\n"
            "    def __post_init__(self) -> None:\n"
            "        if not self.to: raise ValueError('SMS recipient must not be empty')\n"
            "        if not self.text: raise ValueError('SMS text must not be empty')\n\n"
            "@dataclass(frozen=True, slots=True)\nclass SmsReceipt:\n"
            "    group_id: str\n\n"
            "class SmsDelivery(Protocol):\n"
            "    async def send(self, message: SmsMessage) -> SmsReceipt: ...\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from .protocol import SmsMessage, SmsReceipt\n\nclass FakeSmsDelivery:\n"
            "    def __init__(self) -> None: self.messages: list[SmsMessage] = []\n\n"
            "    async def send(self, message: SmsMessage) -> SmsReceipt:\n"
            "        self.messages.append(message)\n        return SmsReceipt(group_id=f'fake-{len(self.messages)}')\n\n"
            "    async def aclose(self) -> None: return None\n"
        )

    @staticmethod
    def _render_solapi() -> str:
        return (
            "from __future__ import annotations\n\nimport asyncio\n\n"
            "from .config import SmsConfig\nfrom .protocol import SmsMessage, SmsReceipt\n\n"
            "class SolapiSmsDelivery:\n"
            "    def __init__(self, config: SmsConfig) -> None:\n        self._config = config\n\n"
            "    async def send(self, message: SmsMessage) -> SmsReceipt:\n"
            "        return await asyncio.wait_for(asyncio.to_thread(self._send_sync, message), self._config.timeout_seconds)\n\n"
            "    def _send_sync(self, message: SmsMessage) -> SmsReceipt:\n"
            "        from solapi import SolapiMessageService\n        from solapi.model import RequestMessage\n"
            "        service = SolapiMessageService(api_key=self._config.api_key, api_secret=self._config.api_secret)\n"
            "        response = service.send(RequestMessage(from_=self._config.sender, to=message.to, text=message.text))\n"
            "        return SmsReceipt(group_id=response.group_info.group_id)\n\n"
            "    async def aclose(self) -> None: return None\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n\nfrom .config import SmsConfig\n"
            "from .protocol import SmsDelivery, SmsMessage, SmsReceipt\n\n"
            "class SmsSender:\n"
            "    def __init__(self, delivery: SmsDelivery) -> None: self._delivery = delivery\n\n"
            "    @classmethod\n    def from_environment(cls) -> SmsSender:\n"
            "        from .solapi import SolapiSmsDelivery\n        return cls(SolapiSmsDelivery(SmsConfig.from_environment()))\n\n"
            "    async def send(self, message: SmsMessage) -> SmsReceipt: return await self._delivery.send(message)\n\n"
            "    async def aclose(self) -> None: await self._delivery.aclose()\n"
        )
