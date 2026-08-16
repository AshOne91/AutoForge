from __future__ import annotations

from pathlib import Path

HOST_PORT_KEYS = frozenset(
    {
        "APPLICATION_PORT",
        "POSTGRES_PORT",
        "RABBITMQ_AMQP_PORT",
        "RABBITMQ_MANAGEMENT_PORT",
        "AIRFLOW_PORT",
        "QDRANT_HTTP_PORT",
        "QDRANT_GRPC_PORT",
        "OPENSEARCH_PORT",
        "OLLAMA_PORT",
        "ELASTICSEARCH_PORT",
        "KIBANA_PORT",
        "S3_API_PORT",
        "S3_CONSOLE_PORT",
    }
)


def validate_port_override_files(paths: tuple[Path, ...]) -> dict[int, tuple[str, ...]]:
    """Return published host ports and reject duplicate overrides."""

    published: dict[int, list[str]] = {}
    for path in paths:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = (part.strip() for part in line.split("=", 1))
            if key not in HOST_PORT_KEYS:
                continue
            value = value.strip('"\'')
            try:
                port = int(value)
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {key} must be an integer") from error
            if not 1 <= port <= 65535:
                raise ValueError(f"{path}:{line_number}: {key} must be between 1 and 65535")
            published.setdefault(port, []).append(f"{key} ({path.name})")

    collisions = [
        f"{port}: {', '.join(labels)}"
        for port, labels in sorted(published.items())
        if len(labels) > 1
    ]
    if collisions:
        raise ValueError("host port override collision(s): " + "; ".join(collisions))
    return {port: tuple(labels) for port, labels in published.items()}
