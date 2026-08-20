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
from autoforge.core.specification import EmailSpec, ProjectSpec

EMAIL_GENERATOR_ID: Final = "autoforge.generator.service.email"
EMAIL_GENERATOR_VERSION: Final = "0.1.0"


class EmailGenerator:
    """Generate an async SMTP email delivery boundary."""

    @property
    def generator_id(self) -> str:
        return EMAIL_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return EMAIL_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        email = specification.tooling.email
        if not email.enabled:
            return {}
        root = PurePosixPath("src", specification.project.package_name, "infrastructure", "email")
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(email),
            root / "fake.py": self._render_fake(),
            root / "protocol.py": self._render_protocol(),
            root / "service.py": self._render_service(),
            root / "smtp.py": self._render_smtp(),
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
                    source=f"project:{specification.project.package_name}:email",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .config import EmailConfig\nfrom .fake import FakeEmailDelivery\n"
            "from .protocol import EmailMessage, EmailDelivery\nfrom .service import EmailSender\n"
            "from .smtp import SmtpEmailDelivery\n\n__all__ = [\n"
            '    "EmailConfig",\n    "EmailDelivery",\n    "EmailMessage",\n'
            '    "EmailSender",\n    "FakeEmailDelivery",\n    "SmtpEmailDelivery",\n]\n'
        )

    @staticmethod
    def _render_config(email: EmailSpec) -> str:
        values = {
            "SMTP_HOST_ENV": email.host_environment,
            "SMTP_PORT_ENV": email.port_environment,
            "SMTP_SENDER_ENV": email.sender_environment,
            "SMTP_USERNAME_ENV": email.username_environment,
            "SMTP_PASSWORD_ENV": email.password_environment,
        }
        constants = "".join(f"{name}: Final = {json.dumps(value)}\n" for name, value in values.items())
        return (
            "from __future__ import annotations\n\nimport os\nfrom dataclasses import dataclass\nfrom typing import Final\n\n"
            f"{constants}DEFAULT_USE_STARTTLS: Final = {email.use_starttls!r}\nDEFAULT_TIMEOUT_SECONDS: Final = {email.timeout_seconds!r}\n\n"
            "@dataclass(frozen=True, slots=True)\nclass EmailConfig:\n"
            "    host: str\n    port: int\n    sender: str\n    username: str | None = None\n    password: str | None = None\n"
            "    use_starttls: bool = DEFAULT_USE_STARTTLS\n    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n\n"
            "    @classmethod\n    def from_environment(cls) -> EmailConfig:\n"
            "        username = os.environ.get(SMTP_USERNAME_ENV)\n        password = os.environ.get(SMTP_PASSWORD_ENV)\n"
            "        if bool(username) != bool(password):\n            raise RuntimeError('SMTP username and password must be set together')\n"
            "        return cls(\n            host=_required(SMTP_HOST_ENV),\n            port=_port(SMTP_PORT_ENV),\n            sender=_required(SMTP_SENDER_ENV),\n            username=username, password=password,\n        )\n\n"
            "def _required(name: str) -> str:\n    value = os.environ.get(name)\n    if not value: raise RuntimeError(f'{name} must be set')\n    return value\n\n"
            "def _port(name: str) -> int:\n    try: port = int(_required(name))\n    except ValueError as error: raise RuntimeError(f'{name} must be an integer') from error\n"
            "    if not 1 <= port <= 65535: raise RuntimeError(f'{name} must be between 1 and 65535')\n    return port\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom typing import Protocol\n\n"
            "@dataclass(frozen=True, slots=True)\nclass EmailMessage:\n"
            "    recipients: tuple[str, ...]\n    subject: str\n    text_body: str\n    html_body: str | None = None\n\n"
            "    def __post_init__(self) -> None:\n        if not self.recipients: raise ValueError('email recipients must not be empty')\n\n"
            "class EmailDelivery(Protocol):\n    async def send(self, message: EmailMessage) -> None: ...\n    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from .protocol import EmailMessage\n\nclass FakeEmailDelivery:\n"
            "    def __init__(self) -> None: self.messages: list[EmailMessage] = []\n"
            "    async def send(self, message: EmailMessage) -> None: self.messages.append(message)\n"
            "    async def aclose(self) -> None: return None\n"
        )

    @staticmethod
    def _render_smtp() -> str:
        return (
            "from __future__ import annotations\n\nimport asyncio\nimport smtplib\nimport ssl\nfrom email.message import EmailMessage as MimeEmailMessage\n\n"
            "from .config import EmailConfig\nfrom .protocol import EmailMessage\n\n"
            "class SmtpEmailDelivery:\n"
            "    def __init__(self, config: EmailConfig) -> None: self._config = config\n\n"
            "    async def send(self, message: EmailMessage) -> None:\n        await asyncio.to_thread(self._send_sync, message)\n\n"
            "    def _send_sync(self, message: EmailMessage) -> None:\n"
            "        mime = MimeEmailMessage()\n        mime['From'] = self._config.sender\n        mime['To'] = ', '.join(message.recipients)\n        mime['Subject'] = message.subject\n        mime.set_content(message.text_body)\n"
            "        if message.html_body is not None: mime.add_alternative(message.html_body, subtype='html')\n"
            "        with smtplib.SMTP(self._config.host, self._config.port, timeout=self._config.timeout_seconds) as client:\n"
            "            if self._config.use_starttls: client.starttls(context=ssl.create_default_context())\n"
            "            if self._config.username is not None: client.login(self._config.username, self._config.password)\n"
            "            client.send_message(mime)\n\n"
            "    async def aclose(self) -> None: return None\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n\nfrom .config import EmailConfig\nfrom .protocol import EmailDelivery, EmailMessage\n\n"
            "class EmailSender:\n"
            "    def __init__(self, delivery: EmailDelivery) -> None: self._delivery = delivery\n\n"
            "    @classmethod\n    def from_environment(cls) -> EmailSender:\n"
            "        from .smtp import SmtpEmailDelivery\n        return cls(SmtpEmailDelivery(EmailConfig.from_environment()))\n\n"
            "    async def send(self, message: EmailMessage) -> None: await self._delivery.send(message)\n"
            "    async def aclose(self) -> None: await self._delivery.aclose()\n"
        )
