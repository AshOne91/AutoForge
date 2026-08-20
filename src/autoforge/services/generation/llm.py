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
from autoforge.core.specification import LlmSpec, ProjectSpec

LLM_GENERATOR_ID: Final = "autoforge.generator.service.llm"
LLM_GENERATOR_VERSION: Final = "0.1.0"


class LlmGenerator:
    """Generate an async, OpenAI-backed LLM boundary."""

    @property
    def generator_id(self) -> str:
        return LLM_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return LLM_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        llm = specification.tooling.llm
        if not llm.enabled:
            return {}
        root = PurePosixPath("src", specification.project.package_name, "infrastructure", "llm")
        return {
            root / "__init__.py": self._render_init(),
            root / "config.py": self._render_config(llm),
            root / "fake.py": self._render_fake(),
            root / "openai_client.py": self._render_openai_client(),
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
                    source=f"project:{specification.project.package_name}:llm",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _render_init() -> str:
        return (
            "from .config import LlmConfig\nfrom .fake import FakeLlmClient\n"
            "from .openai_client import OpenAIResponsesClient\n"
            "from .protocol import LlmClient, LlmMessage, LlmResponse\n"
            "from .service import LlmService\n\n__all__ = [\n"
            '    "FakeLlmClient",\n    "LlmClient",\n    "LlmConfig",\n'
            '    "LlmMessage",\n    "LlmResponse",\n    "LlmService",\n'
            '    "OpenAIResponsesClient",\n]\n'
        )

    @staticmethod
    def _render_config(llm: LlmSpec) -> str:
        return (
            "from __future__ import annotations\n\nimport os\nfrom dataclasses import dataclass\n"
            "from typing import Final\n\n"
            f"OPENAI_API_KEY_ENV: Final = {json.dumps(llm.api_key_environment)}\n"
            f"DEFAULT_MODEL: Final = {json.dumps(llm.model)}\n"
            f"DEFAULT_TIMEOUT_SECONDS: Final = {llm.timeout_seconds!r}\n\n"
            "@dataclass(frozen=True, slots=True)\nclass LlmConfig:\n"
            "    api_key: str\n    model: str = DEFAULT_MODEL\n"
            "    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS\n\n"
            "    @classmethod\n    def from_environment(cls) -> LlmConfig:\n"
            "        api_key = os.environ.get(OPENAI_API_KEY_ENV)\n"
            "        if not api_key: raise RuntimeError(f'{OPENAI_API_KEY_ENV} must be set')\n"
            "        return cls(api_key=api_key)\n"
        )

    @staticmethod
    def _render_protocol() -> str:
        return (
            "from __future__ import annotations\n\nfrom collections.abc import Sequence\n"
            "from dataclasses import dataclass\nfrom typing import Protocol\n\n"
            "@dataclass(frozen=True, slots=True)\nclass LlmMessage:\n"
            "    role: str\n    content: str\n\n"
            "    def __post_init__(self) -> None:\n"
            "        if not self.role: raise ValueError('LLM message role must not be empty')\n"
            "        if not self.content: raise ValueError('LLM message content must not be empty')\n\n"
            "@dataclass(frozen=True, slots=True)\nclass LlmResponse:\n"
            "    content: str\n    response_id: str | None = None\n\n"
            "class LlmClient(Protocol):\n"
            "    async def respond(self, messages: Sequence[LlmMessage], *, instructions: str | None = None) -> LlmResponse: ...\n"
            "    async def aclose(self) -> None: ...\n"
        )

    @staticmethod
    def _render_fake() -> str:
        return (
            "from collections import deque\nfrom collections.abc import Iterable, Sequence\n\n"
            "from .protocol import LlmMessage, LlmResponse\n\n"
            "class FakeLlmClient:\n"
            "    def __init__(self, responses: Iterable[LlmResponse] = ()) -> None:\n"
            "        self._responses = deque(responses)\n        self.requests: list[tuple[tuple[LlmMessage, ...], str | None]] = []\n\n"
            "    async def respond(self, messages: Sequence[LlmMessage], *, instructions: str | None = None) -> LlmResponse:\n"
            "        self.requests.append((tuple(messages), instructions))\n"
            "        return self._responses.popleft() if self._responses else LlmResponse(content='')\n\n"
            "    async def aclose(self) -> None: return None\n"
        )

    @staticmethod
    def _render_openai_client() -> str:
        return (
            "from __future__ import annotations\n\nfrom collections.abc import Sequence\n\n"
            "from openai import AsyncOpenAI\n\nfrom .config import LlmConfig\n"
            "from .protocol import LlmMessage, LlmResponse\n\n"
            "class OpenAIResponsesClient:\n"
            "    def __init__(self, config: LlmConfig, *, client: AsyncOpenAI | None = None) -> None:\n"
            "        self._config = config\n        self._client = client or AsyncOpenAI(api_key=config.api_key, timeout=config.timeout_seconds)\n        self._owns_client = client is None\n\n"
            "    async def respond(self, messages: Sequence[LlmMessage], *, instructions: str | None = None) -> LlmResponse:\n"
            "        response = await self._client.responses.create(\n"
            "            model=self._config.model,\n            instructions=instructions,\n"
            "            input=[{'role': message.role, 'content': message.content} for message in messages],\n"
            "            store=False,\n        )\n"
            "        return LlmResponse(content=response.output_text, response_id=response.id)\n\n"
            "    async def aclose(self) -> None:\n"
            "        if self._owns_client: await self._client.close()\n"
        )

    @staticmethod
    def _render_service() -> str:
        return (
            "from __future__ import annotations\n\nfrom collections.abc import Sequence\n\n"
            "from .config import LlmConfig\nfrom .protocol import LlmClient, LlmMessage, LlmResponse\n\n"
            "class LlmService:\n"
            "    def __init__(self, client: LlmClient) -> None: self._client = client\n\n"
            "    @classmethod\n    def from_environment(cls) -> LlmService:\n"
            "        from .openai_client import OpenAIResponsesClient\n"
            "        return cls(OpenAIResponsesClient(LlmConfig.from_environment()))\n\n"
            "    async def respond(self, messages: Sequence[LlmMessage], *, instructions: str | None = None) -> LlmResponse:\n"
            "        return await self._client.respond(messages, instructions=instructions)\n\n"
            "    async def aclose(self) -> None: await self._client.aclose()\n"
        )
