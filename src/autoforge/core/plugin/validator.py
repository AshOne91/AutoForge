from collections.abc import Awaitable, Callable

from autoforge.core.plugin.metadata import (
    PluginCapability,
    PluginMetadata,
    validate_plugin_api_version,
)
from autoforge.core.registry.registry import Registry


class ValidatorPluginAdapter[RequestT, ResultT]:
    """비동기 Validator 호출과 Plugin Metadata를 결합한다."""

    def __init__(
        self,
        *,
        validator_id: str,
        validator_version: str,
        validate: Callable[[RequestT], Awaitable[ResultT]],
        metadata: PluginMetadata,
    ) -> None:
        validate_plugin_api_version(metadata)
        if PluginCapability.VALIDATOR not in metadata.capabilities:
            raise ValueError("Validator Plugin에는 validator Capability가 필요합니다.")
        if metadata.name != validator_id:
            raise ValueError("Plugin 이름과 Validator ID가 일치해야 합니다.")
        if metadata.version != validator_version:
            raise ValueError("Plugin 버전과 Validator 버전이 일치해야 합니다.")
        self._validator_id = validator_id
        self._validator_version = validator_version
        self._validate = validate
        self._metadata = metadata

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    @property
    def validator_id(self) -> str:
        return self._validator_id

    @property
    def validator_version(self) -> str:
        return self._validator_version

    async def validate(self, request: RequestT) -> ResultT:
        return await self._validate(request)


class ValidatorPluginRegistry[RequestT, ResultT]:
    """요청과 결과 타입별 Validator Plugin 저장소."""

    def __init__(self) -> None:
        self._registry = Registry[ValidatorPluginAdapter[RequestT, ResultT]]()

    def register(self, plugin: ValidatorPluginAdapter[RequestT, ResultT]) -> None:
        self._registry.register(plugin.validator_id, plugin)

    def get(
        self,
        validator_id: str,
    ) -> ValidatorPluginAdapter[RequestT, ResultT]:
        return self._registry.get(validator_id)

    def exists(self, validator_id: str) -> bool:
        return self._registry.exists(validator_id)

    def names(self) -> list[str]:
        return self._registry.names()

    def unregister(self, validator_id: str) -> None:
        self._registry.unregister(validator_id)
