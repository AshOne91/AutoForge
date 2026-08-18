from pathlib import Path

import yaml

from autoforge.core.config.loader import ConfigLoader

PROFILE_ROOT = Path("deploy/control-plane")


def test_control_plane_profile_has_private_database_and_liveness_probe() -> None:
    compose = yaml.safe_load((PROFILE_ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert set(services) == {"control-db", "control-plane"}
    assert "ports" not in services["control-db"]
    assert services["control-plane"]["restart"] == "unless-stopped"
    assert services["control-plane"]["depends_on"] == {
        "control-db": {"condition": "service_healthy"}
    }
    assert services["control-plane"]["environment"] == {
        "AUTOFORGE_DATABASE_URL": "${AUTOFORGE_DATABASE_URL:?set AUTOFORGE_DATABASE_URL}",
        "AUTOFORGE_CONTROL_PLANE_TOKEN": "${CONTROL_PLANE_API_TOKEN:?set CONTROL_PLANE_API_TOKEN}",
    }
    assert "/health" in services["control-plane"]["healthcheck"]["test"][-1]


def test_control_plane_profile_config_and_secret_example_are_valid() -> None:
    settings = ConfigLoader.load(PROFILE_ROOT / "autoforge.yaml")
    environment = (PROFILE_ROOT / ".env.example").read_text(encoding="utf-8")
    dockerfile = (PROFILE_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert settings.workspace.output == "/workspace/output"
    assert "AUTOFORGE_DATABASE_URL=" in environment
    assert "CONTROL_PLANE_API_TOKEN=" in environment
    assert 'pip install --no-cache-dir ".[server]"' in dockerfile
    assert '"autoforge.main", "server"' in dockerfile
