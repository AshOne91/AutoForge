import pytest

from autoforge.core.plugin import (
    PluginDependency,
    PluginMetadata,
    PluginPermission,
)


def test_metadata_accepts_versioned_dependencies_and_permissions() -> None:
    metadata = PluginMetadata(
        name="autoforge.generator.kubernetes",
        version="0.1.0",
        requirements=(
            PluginDependency(
                plugin_id="autoforge.generator.container",
                required_version="0.1.0",
            ),
        ),
        permissions=(
            PluginPermission.FILESYSTEM_READ,
            PluginPermission.FILESYSTEM_WRITE,
        ),
    )

    assert metadata.requirements[0].required_version == "0.1.0"
    assert metadata.permissions == (
        PluginPermission.FILESYSTEM_READ,
        PluginPermission.FILESYSTEM_WRITE,
    )


@pytest.mark.parametrize(
    "requirements",
    [
        (
            PluginDependency(
                plugin_id="autoforge.generator.kubernetes",
                required_version="0.1.0",
            ),
        ),
        (
            PluginDependency(plugin_id="dependency", required_version="1"),
            PluginDependency(plugin_id="dependency", required_version="2"),
        ),
    ],
)
def test_metadata_rejects_self_or_duplicate_requirements(
    requirements: tuple[PluginDependency, ...],
) -> None:
    with pytest.raises(ValueError, match="자기 자신|중복"):
        PluginMetadata(
            name="autoforge.generator.kubernetes",
            version="0.1.0",
            requirements=requirements,
        )


def test_metadata_rejects_duplicate_legacy_and_versioned_dependency() -> None:
    with pytest.raises(ValueError, match="중복"):
        PluginMetadata(
            name="plugin",
            version="0.1.0",
            dependencies=["dependency"],
            requirements=(
                PluginDependency(
                    plugin_id="dependency",
                    required_version="1.0.0",
                ),
            ),
        )


def test_metadata_rejects_duplicate_permissions() -> None:
    with pytest.raises(ValueError, match="권한"):
        PluginMetadata(
            name="plugin",
            version="0.1.0",
            permissions=(
                PluginPermission.NETWORK_ACCESS,
                PluginPermission.NETWORK_ACCESS,
            ),
        )


def test_dependency_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="Plugin ID"):
        PluginDependency(plugin_id="", required_version="1")
    with pytest.raises(ValueError, match="Plugin 버전"):
        PluginDependency(plugin_id="dependency", required_version="")
