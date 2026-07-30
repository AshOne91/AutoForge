import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from autoforge.core.plugin.metadata import (
    PluginCapability,
    PluginDependency,
    PluginMetadata,
    PluginPermission,
    validate_plugin_api_version,
)

PLUGIN_MANIFEST_FILENAME: Final = "plugin.json"
PLUGIN_METADATA_FIELDS: Final = frozenset(
    {
        "name",
        "version",
        "description",
        "author",
        "dependencies",
        "api_version",
        "capabilities",
        "supported_specification_versions",
        "requirements",
        "permissions",
    }
)


class PluginLoaderError(RuntimeError):
    """Plugin 후보 또는 Metadata를 안전하게 발견할 수 없을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class PluginCandidate:
    directory: Path
    manifest_path: Path
    metadata: PluginMetadata


class PluginLoader:
    """명시된 디렉터리에서 실행 없이 Plugin Metadata만 발견한다."""

    def __init__(self, plugin_directory: Path) -> None:
        self._plugin_directory = plugin_directory

    def discover(self) -> tuple[PluginCandidate, ...]:
        root = self._validate_root()
        candidates: list[PluginCandidate] = []
        plugin_ids: set[str] = set()

        for directory in sorted(root.iterdir(), key=lambda path: path.name):
            if directory.is_symlink():
                raise PluginLoaderError(
                    f"Plugin 디렉터리는 Symlink일 수 없습니다: {directory}"
                )
            if not directory.is_dir():
                continue
            self._validate_inside_root(root, directory)
            manifest_path = directory / PLUGIN_MANIFEST_FILENAME
            if not manifest_path.exists():
                continue
            if manifest_path.is_symlink() or not manifest_path.is_file():
                raise PluginLoaderError(
                    f"Plugin Manifest가 안전한 파일이 아닙니다: {manifest_path}"
                )
            metadata = self._load_metadata(manifest_path)
            if metadata.name in plugin_ids:
                raise PluginLoaderError(
                    f"중복 Plugin ID가 발견되었습니다: {metadata.name}"
                )
            plugin_ids.add(metadata.name)
            candidates.append(
                PluginCandidate(
                    directory=directory.resolve(),
                    manifest_path=manifest_path.resolve(),
                    metadata=metadata,
                )
            )
        return tuple(candidates)

    def _validate_root(self) -> Path:
        if self._plugin_directory.is_symlink():
            raise PluginLoaderError(
                f"Plugin 루트는 Symlink일 수 없습니다: {self._plugin_directory}"
            )
        root = self._plugin_directory.resolve()
        if not root.is_dir():
            raise PluginLoaderError(
                f"Plugin 디렉터리를 찾을 수 없습니다: {self._plugin_directory}"
            )
        return root

    @staticmethod
    def _validate_inside_root(root: Path, candidate: Path) -> None:
        try:
            candidate.resolve().relative_to(root)
        except ValueError as error:
            raise PluginLoaderError(
                f"Plugin 후보가 루트 밖을 가리킵니다: {candidate}"
            ) from error

    def _load_metadata(self, manifest_path: Path) -> PluginMetadata:
        try:
            document = json.loads(manifest_path.read_bytes())
            if not isinstance(document, dict):
                raise TypeError("Plugin Manifest 최상위 값은 객체여야 합니다.")
            unknown_fields = set(document) - PLUGIN_METADATA_FIELDS
            if unknown_fields:
                raise ValueError(f"알 수 없는 Metadata 필드: {sorted(unknown_fields)}")
            metadata = self._metadata_from_document(document)
            validate_plugin_api_version(metadata)
            return metadata
        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
        ) as error:
            raise PluginLoaderError(
                f"Plugin Manifest가 유효하지 않습니다: {manifest_path}"
            ) from error

    @staticmethod
    def _metadata_from_document(document: dict[str, object]) -> PluginMetadata:
        requirements_value = document.get("requirements", [])
        if not isinstance(requirements_value, list):
            raise TypeError("requirements는 배열이어야 합니다.")
        requirements = tuple(
            PluginLoader._dependency_from_document(requirement)
            for requirement in requirements_value
        )
        return PluginMetadata(
            name=PluginLoader._required_string(document, "name"),
            version=PluginLoader._required_string(document, "version"),
            description=PluginLoader._optional_string(document, "description"),
            author=PluginLoader._optional_string(document, "author"),
            dependencies=PluginLoader._string_list(document, "dependencies"),
            api_version=PluginLoader._optional_string(
                document,
                "api_version",
                default="1",
            ),
            capabilities=tuple(
                PluginCapability(value)
                for value in PluginLoader._string_list(document, "capabilities")
            ),
            supported_specification_versions=tuple(
                PluginLoader._string_list(
                    document,
                    "supported_specification_versions",
                )
            ),
            requirements=requirements,
            permissions=tuple(
                PluginPermission(value)
                for value in PluginLoader._string_list(document, "permissions")
            ),
        )

    @staticmethod
    def _dependency_from_document(value: object) -> PluginDependency:
        if not isinstance(value, dict):
            raise TypeError("Plugin 의존성은 객체여야 합니다.")
        if set(value) != {"plugin_id", "required_version"}:
            raise ValueError("Plugin 의존성 필드가 올바르지 않습니다.")
        return PluginDependency(
            plugin_id=PluginLoader._required_string(value, "plugin_id"),
            required_version=PluginLoader._required_string(
                value,
                "required_version",
            ),
        )

    @staticmethod
    def _required_string(document: dict[str, object], key: str) -> str:
        value = document[key]
        if not isinstance(value, str):
            raise TypeError(f"{key}는 문자열이어야 합니다.")
        return value

    @staticmethod
    def _optional_string(
        document: dict[str, object],
        key: str,
        *,
        default: str = "",
    ) -> str:
        value = document.get(key, default)
        if not isinstance(value, str):
            raise TypeError(f"{key}는 문자열이어야 합니다.")
        return value

    @staticmethod
    def _string_list(document: dict[str, object], key: str) -> list[str]:
        value = document.get(key, [])
        if not isinstance(value, list) or any(
            not isinstance(item, str) for item in value
        ):
            raise TypeError(f"{key}는 문자열 배열이어야 합니다.")
        return value
