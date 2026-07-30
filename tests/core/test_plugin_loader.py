import json
from pathlib import Path

import pytest

from autoforge.core.plugin import (
    Plugin,
    PluginCapability,
    PluginLoader,
    PluginLoaderError,
    PluginPermission,
)
from autoforge.core.plugin.manager import PluginManager


def write_manifest(
    plugin_root: Path,
    directory_name: str,
    *,
    plugin_id: str,
    api_version: str = "1",
    dependencies: list[str] | None = None,
    requirements: list[dict[str, str]] | None = None,
    version: str = "0.1.0",
    entrypoint: str | None = None,
) -> Path:
    directory = plugin_root / directory_name
    directory.mkdir(parents=True)
    manifest_path = directory / "plugin.json"
    document = {
        "name": plugin_id,
        "version": version,
        "api_version": api_version,
        "capabilities": ["generator"],
        "supported_specification_versions": ["1"],
        "dependencies": dependencies or [],
        "requirements": requirements or [],
        "permissions": ["filesystem_read"],
    }
    if entrypoint is not None:
        document["entrypoint"] = entrypoint
    manifest_path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )
    return manifest_path


def write_plugin_module(
    manifest_path: Path,
    *,
    plugin_id: str,
    dependencies: list[str] | None = None,
    metadata_name: str | None = None,
    raises: bool = False,
) -> None:
    factory_body = (
        "    raise RuntimeError('factory failed')\n"
        if raises
        else "    return LoadedPlugin()\n"
    )
    (manifest_path.parent / "plugin_impl.py").write_text(
        "from autoforge.core.plugin import Plugin, PluginCapability, "
        "PluginMetadata, PluginPermission\n"
        "from autoforge.models.plugin_result import PluginResult\n"
        "\n"
        "\n"
        "class LoadedPlugin(Plugin):\n"
        "    @property\n"
        "    def metadata(self) -> PluginMetadata:\n"
        "        return PluginMetadata(\n"
        f"            name={metadata_name or plugin_id!r},\n"
        "            version='0.1.0',\n"
        "            api_version='1',\n"
        "            capabilities=(PluginCapability.GENERATOR,),\n"
        "            supported_specification_versions=('1',),\n"
        f"            dependencies={dependencies or []!r},\n"
        "            permissions=(PluginPermission.FILESYSTEM_READ,),\n"
        "            entrypoint='plugin_impl:create_plugin',\n"
        "        )\n"
        "\n"
        "    def initialize(self) -> None:\n"
        "        pass\n"
        "\n"
        "    def execute(self, context: object) -> PluginResult:\n"
        "        return PluginResult(success=True, message='loaded')\n"
        "\n"
        "\n"
        "def create_plugin() -> Plugin:\n"
        f"{factory_body}",
        encoding="utf-8",
    )


def test_loader_discovers_metadata_in_directory_order(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(plugin_root, "second", plugin_id="plugin.second")
    write_manifest(
        plugin_root,
        "first",
        plugin_id="plugin.first",
        requirements=[
            {
                "plugin_id": "autoforge.generator.container",
                "required_version": "0.1.0",
            }
        ],
    )
    (plugin_root / "README.md").write_text("ignored", encoding="utf-8")
    (plugin_root / "without-manifest").mkdir()

    candidates = PluginLoader(plugin_root).discover()

    assert [candidate.directory.name for candidate in candidates] == [
        "first",
        "second",
    ]
    assert [candidate.metadata.name for candidate in candidates] == [
        "plugin.first",
        "plugin.second",
    ]
    assert candidates[0].metadata.capabilities == (PluginCapability.GENERATOR,)
    assert candidates[0].metadata.permissions == (PluginPermission.FILESYSTEM_READ,)
    assert candidates[0].metadata.requirements[0].required_version == "0.1.0"


def test_loader_resolves_dependencies_before_dependents(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(
        plugin_root, "app", plugin_id="plugin.app", dependencies=["plugin.api"]
    )
    write_manifest(
        plugin_root,
        "api",
        plugin_id="plugin.api",
        requirements=[
            {
                "plugin_id": "plugin.storage",
                "required_version": "2.0.0",
            }
        ],
    )
    write_manifest(
        plugin_root,
        "storage",
        plugin_id="plugin.storage",
        version="2.0.0",
    )

    ordered = PluginLoader(plugin_root).resolve_load_order()

    assert [candidate.metadata.name for candidate in ordered] == [
        "plugin.storage",
        "plugin.api",
        "plugin.app",
    ]


def test_loader_rejects_missing_dependency(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(
        plugin_root,
        "app",
        plugin_id="plugin.app",
        dependencies=["plugin.missing"],
    )

    with pytest.raises(PluginLoaderError, match="찾을 수 없습니다"):
        PluginLoader(plugin_root).resolve_load_order()


def test_loader_rejects_dependency_version_mismatch(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(
        plugin_root,
        "app",
        plugin_id="plugin.app",
        requirements=[
            {
                "plugin_id": "plugin.api",
                "required_version": "2.0.0",
            }
        ],
    )
    write_manifest(plugin_root, "api", plugin_id="plugin.api", version="1.0.0")

    with pytest.raises(PluginLoaderError, match="버전이 일치하지"):
        PluginLoader(plugin_root).resolve_load_order()


def test_loader_rejects_circular_dependency(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(
        plugin_root,
        "first",
        plugin_id="plugin.first",
        dependencies=["plugin.second"],
    )
    write_manifest(
        plugin_root,
        "second",
        plugin_id="plugin.second",
        dependencies=["plugin.first"],
    )

    with pytest.raises(PluginLoaderError, match="순환 의존성"):
        PluginLoader(plugin_root).resolve_load_order()


def test_trusted_loader_registers_plugins_in_dependency_order(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    dependency_manifest = write_manifest(
        plugin_root,
        "dependency",
        plugin_id="plugin.dependency",
        entrypoint="plugin_impl:create_plugin",
    )
    write_plugin_module(
        dependency_manifest,
        plugin_id="plugin.dependency",
    )
    app_manifest = write_manifest(
        plugin_root,
        "app",
        plugin_id="plugin.app",
        dependencies=["plugin.dependency"],
        entrypoint="plugin_impl:create_plugin",
    )
    write_plugin_module(
        app_manifest,
        plugin_id="plugin.app",
        dependencies=["plugin.dependency"],
    )
    manager = RecordingPluginManager()

    plugins = PluginLoader(plugin_root).load_trusted(manager)

    assert [plugin.metadata.name for plugin in plugins] == [
        "plugin.dependency",
        "plugin.app",
    ]
    assert manager.registered_order == ["plugin.dependency", "plugin.app"]


def test_trusted_loader_rejects_manifest_metadata_mismatch(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    manifest_path = write_manifest(
        plugin_root,
        "mismatch",
        plugin_id="plugin.expected",
        entrypoint="plugin_impl:create_plugin",
    )
    write_plugin_module(
        manifest_path,
        plugin_id="plugin.expected",
        metadata_name="plugin.different",
    )
    manager = PluginManager()

    with pytest.raises(PluginLoaderError, match="Metadata"):
        PluginLoader(plugin_root).load_trusted(manager)

    assert manager.list_plugins() == []


def test_trusted_loader_rejects_invalid_entrypoint(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(
        plugin_root,
        "invalid",
        plugin_id="plugin.invalid",
        entrypoint="../outside:create_plugin",
    )

    with pytest.raises(PluginLoaderError, match="Entrypoint"):
        PluginLoader(plugin_root).load_trusted(PluginManager())


def test_trusted_loader_rejects_non_plugin_factory_result(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    manifest_path = write_manifest(
        plugin_root,
        "invalid",
        plugin_id="plugin.invalid",
        entrypoint="plugin_impl:create_plugin",
    )
    (manifest_path.parent / "plugin_impl.py").write_text(
        "def create_plugin() -> object:\n    return object()\n",
        encoding="utf-8",
    )

    with pytest.raises(PluginLoaderError, match="Plugin을 반환하지"):
        PluginLoader(plugin_root).load_trusted(PluginManager())


def test_trusted_loader_does_not_partially_register_factory_failure(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    good_manifest = write_manifest(
        plugin_root,
        "first",
        plugin_id="plugin.first",
        entrypoint="plugin_impl:create_plugin",
    )
    write_plugin_module(good_manifest, plugin_id="plugin.first")
    failed_manifest = write_manifest(
        plugin_root,
        "second",
        plugin_id="plugin.second",
        entrypoint="plugin_impl:create_plugin",
    )
    write_plugin_module(
        failed_manifest,
        plugin_id="plugin.second",
        raises=True,
    )
    manager = PluginManager()

    with pytest.raises(PluginLoaderError, match="Factory 실행"):
        PluginLoader(plugin_root).load_trusted(manager)

    assert manager.list_plugins() == []


def test_trusted_loader_rolls_back_registration_failure(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    for plugin_id in ("plugin.first", "plugin.second"):
        manifest_path = write_manifest(
            plugin_root,
            plugin_id,
            plugin_id=plugin_id,
            entrypoint="plugin_impl:create_plugin",
        )
        write_plugin_module(manifest_path, plugin_id=plugin_id)
    manager = FailingPluginManager("plugin.second")

    with pytest.raises(PluginLoaderError, match="일괄 등록"):
        PluginLoader(plugin_root).load_trusted(manager)

    assert manager.list_plugins() == []


class RecordingPluginManager(PluginManager):
    def __init__(self) -> None:
        super().__init__()
        self.registered_order: list[str] = []

    def register(self, plugin: Plugin) -> None:
        super().register(plugin)
        self.registered_order.append(plugin.metadata.name)


class FailingPluginManager(PluginManager):
    def __init__(self, failed_plugin_id: str) -> None:
        super().__init__()
        self._failed_plugin_id = failed_plugin_id

    def register(self, plugin: Plugin) -> None:
        if plugin.metadata.name == self._failed_plugin_id:
            raise RuntimeError("registration failed")
        super().register(plugin)


def test_loader_does_not_import_plugin_code(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    manifest_path = write_manifest(
        plugin_root,
        "safe",
        plugin_id="plugin.safe",
    )
    marker = tmp_path / "executed.txt"
    (manifest_path.parent / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )

    loader = PluginLoader(plugin_root)
    loader.resolve_load_order(loader.discover())

    assert not marker.exists()


@pytest.mark.parametrize(
    "content",
    [
        b"{not json",
        json.dumps([]).encode(),
        json.dumps({"name": "missing-version"}).encode(),
        json.dumps(
            {
                "name": "unknown-field",
                "version": "1",
                "unexpected": True,
            }
        ).encode(),
        b"\xff",
    ],
)
def test_loader_rejects_invalid_manifest(
    tmp_path: Path,
    content: bytes,
) -> None:
    manifest_path = tmp_path / "plugins" / "invalid" / "plugin.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(content)

    with pytest.raises(PluginLoaderError, match="유효하지"):
        PluginLoader(tmp_path / "plugins").discover()


def test_loader_rejects_unsupported_api_version(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(
        plugin_root,
        "future",
        plugin_id="plugin.future",
        api_version="999",
    )

    with pytest.raises(PluginLoaderError, match="유효하지"):
        PluginLoader(plugin_root).discover()


def test_loader_rejects_duplicate_plugin_id(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(plugin_root, "first", plugin_id="plugin.duplicate")
    write_manifest(plugin_root, "second", plugin_id="plugin.duplicate")

    with pytest.raises(PluginLoaderError, match="중복 Plugin ID"):
        PluginLoader(plugin_root).discover()


def test_loader_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(PluginLoaderError, match="찾을 수 없습니다"):
        PluginLoader(tmp_path / "missing").discover()


def test_loader_rejects_symlink_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = tmp_path / "plugins"
    plugin_directory = plugin_root / "linked"
    plugin_directory.mkdir(parents=True)
    manifest_path = plugin_directory / "plugin.json"
    manifest_path.write_text("{}", encoding="utf-8")
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == manifest_path or original_is_symlink(path),
    )

    with pytest.raises(PluginLoaderError, match="안전한 파일"):
        PluginLoader(plugin_root).discover()
