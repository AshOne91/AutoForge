from dataclasses import dataclass, field
from enum import StrEnum


class PluginCapability(StrEnum):
    GENERATOR = "generator"
    VALIDATOR = "validator"
    BUILDER = "builder"
    GIT = "git"
    CI_CD = "ci_cd"


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
