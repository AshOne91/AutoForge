from pathlib import Path

import pytest

from autoforge.services.port_preflight import validate_port_override_files


def test_validate_port_override_files_accepts_unique_ports(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APPLICATION_PORT=49400\nPOSTGRES_PORT='49410'\nIGNORED=49400\n",
        encoding="utf-8",
    )

    ports = validate_port_override_files((env_file,))

    assert sorted(ports) == [49400, 49410]


def test_validate_port_override_files_rejects_collisions_across_files(
    tmp_path: Path,
) -> None:
    first = tmp_path / "integration.env"
    second = tmp_path / "elk.env"
    first.write_text("APPLICATION_PORT=49400\n", encoding="utf-8")
    second.write_text("ELASTICSEARCH_PORT=49400\n", encoding="utf-8")

    with pytest.raises(ValueError, match="49400.*APPLICATION_PORT.*ELASTICSEARCH_PORT"):
        validate_port_override_files((first, second))


def test_validate_port_override_files_rejects_invalid_port(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("APPLICATION_PORT=not-a-port\n", encoding="utf-8")

    with pytest.raises(ValueError, match="APPLICATION_PORT must be an integer"):
        validate_port_override_files((env_file,))
