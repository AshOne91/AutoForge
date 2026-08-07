from pathlib import Path

import pytest
from pydantic import ValidationError

from autoforge.core.config import ConfigLoader, ConfigManager, Settings


def settings_data() -> dict[str, object]:
    return {
        "project": {"name": "AutoForge", "version": "0.1.0"},
        "workspace": {"output": "./output"},
        "logging": {"level": "INFO"},
    }


def test_config_manager_uses_injected_settings() -> None:
    settings = Settings.model_validate(settings_data())

    manager = ConfigManager(settings)

    assert manager.settings is settings
    assert manager.project.name == "AutoForge"
    assert manager.workspace.output == "./output"
    assert manager.logging.level == "INFO"
    assert manager.plugins.enabled == []
    assert manager.git_automation.enabled is False
    assert manager.git_automation.push_remote_name == "origin"


def test_config_manager_loads_explicit_file(tmp_path: Path) -> None:
    config_path = tmp_path / "autoforge.yaml"
    config_path.write_text(
        """project:
  name: AutoForge
  version: "0.1.0"
workspace:
  output: "./output"
logging:
  level: INFO
""",
        encoding="utf-8",
    )

    manager = ConfigManager.from_file(config_path)

    assert manager.project.version == "0.1.0"
    assert manager.plugins.enabled == []


def test_config_loader_requires_explicit_existing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="설정 파일"):
        ConfigLoader.load(tmp_path / "missing.yaml")


def test_config_loader_rejects_non_mapping_document(tmp_path: Path) -> None:
    config_path = tmp_path / "autoforge.yaml"
    config_path.write_text("- invalid\n- document\n", encoding="utf-8")

    with pytest.raises(TypeError, match="Mapping"):
        ConfigLoader.load(config_path)


def test_settings_reject_unknown_fields() -> None:
    data = settings_data()
    data["unknown"] = True

    with pytest.raises(ValidationError, match="unknown"):
        Settings.model_validate(data)


def test_git_automation_config_is_optional_and_validated() -> None:
    data = settings_data()
    data["git_automation"] = {
        "enabled": True,
        "secret_names": {"git/github/token": "AUTOFORGE_GITHUB_TOKEN"},
        "github_api_timeout_seconds": 15,
        "push_remote_name": "origin",
        "pull_request_base_branch": "main",
    }

    settings = Settings.model_validate(data)

    assert settings.git_automation.enabled is True
    assert settings.git_automation.secret_names == {
        "git/github/token": "AUTOFORGE_GITHUB_TOKEN"
    }
    assert settings.git_automation.github_api_timeout_seconds == 15

    data["git_automation"] = {"enabled": True}
    with pytest.raises(ValidationError, match="secret mapping"):
        Settings.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("github_api_timeout_seconds", 0),
        ("push_remote_name", ""),
        ("pull_request_base_branch", ""),
        ("pull_request_title", ""),
    ),
)
def test_git_automation_config_rejects_invalid_values(
    field: str,
    value: object,
) -> None:
    data = settings_data()
    data["git_automation"] = {field: value}

    with pytest.raises(ValidationError):
        Settings.model_validate(data)
