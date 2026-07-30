import json
from pathlib import Path

import pytest

from autoforge.core.plugin import (
    PluginCapability,
    PluginLoader,
    PluginLoaderError,
    PluginPermission,
)


def write_manifest(
    plugin_root: Path,
    directory_name: str,
    *,
    plugin_id: str,
    api_version: str = "1",
) -> Path:
    directory = plugin_root / directory_name
    directory.mkdir(parents=True)
    manifest_path = directory / "plugin.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": plugin_id,
                "version": "0.1.0",
                "api_version": api_version,
                "capabilities": ["generator"],
                "supported_specification_versions": ["1"],
                "requirements": [
                    {
                        "plugin_id": "autoforge.generator.container",
                        "required_version": "0.1.0",
                    }
                ],
                "permissions": ["filesystem_read"],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_loader_discovers_metadata_in_directory_order(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_manifest(plugin_root, "second", plugin_id="plugin.second")
    write_manifest(plugin_root, "first", plugin_id="plugin.first")
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

    PluginLoader(plugin_root).discover()

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
