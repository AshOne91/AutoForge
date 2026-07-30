from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

CURRENT_PLUGIN_API_VERSION: Final = "1"


class PluginCapability(StrEnum):
    GENERATOR = "generator"
    VALIDATOR = "validator"
    BUILDER = "builder"
    GIT = "git"
    CI_CD = "ci_cd"


class PluginPermission(StrEnum):
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    PROCESS_EXECUTE = "process_execute"
    NETWORK_ACCESS = "network_access"


@dataclass(frozen=True, slots=True)
class PluginDependency:
    plugin_id: str
    required_version: str

    def __post_init__(self) -> None:
        if not self.plugin_id.strip():
            raise ValueError("의존 Plugin ID는 비어 있을 수 없습니다.")
        if not self.required_version.strip():
            raise ValueError("의존 Plugin 버전은 비어 있을 수 없습니다.")


@dataclass(slots=True)
class PluginMetadata:
    """
    Plugin Manifest
    """

    name: str

    version: str

    description: str = ""

    author: str = ""

    dependencies: list[str] = field(default_factory=list)

    api_version: str = "1"

    capabilities: tuple[PluginCapability, ...] = ()

    supported_specification_versions: tuple[str, ...] = ()

    requirements: tuple[PluginDependency, ...] = ()

    permissions: tuple[PluginPermission, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Plugin 이름은 비어 있을 수 없습니다.")
        if not self.version.strip():
            raise ValueError("Plugin 버전은 비어 있을 수 없습니다.")
        if not self.api_version.strip():
            raise ValueError("Plugin API 버전은 비어 있을 수 없습니다.")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("Plugin Capability는 중복될 수 없습니다.")
        if len(self.supported_specification_versions) != len(
            set(self.supported_specification_versions)
        ):
            raise ValueError("지원 Specification 버전은 중복될 수 없습니다.")
        legacy_dependency_ids = [dependency.strip() for dependency in self.dependencies]
        if any(not dependency_id for dependency_id in legacy_dependency_ids):
            raise ValueError("의존 Plugin ID는 비어 있을 수 없습니다.")
        requirement_ids = [requirement.plugin_id for requirement in self.requirements]
        all_dependency_ids = [*legacy_dependency_ids, *requirement_ids]
        if self.name in all_dependency_ids:
            raise ValueError("Plugin은 자기 자신에게 의존할 수 없습니다.")
        if len(all_dependency_ids) != len(set(all_dependency_ids)):
            raise ValueError("의존 Plugin은 중복될 수 없습니다.")
        if len(self.permissions) != len(set(self.permissions)):
            raise ValueError("Plugin 권한은 중복될 수 없습니다.")


def validate_plugin_api_version(metadata: PluginMetadata) -> None:
    if metadata.api_version != CURRENT_PLUGIN_API_VERSION:
        raise ValueError(f"지원하지 않는 Plugin API 버전입니다: {metadata.api_version}")
