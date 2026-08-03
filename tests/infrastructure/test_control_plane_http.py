from pathlib import Path

from fastapi.testclient import TestClient

from autoforge.application.generation import GenerationSubmissionService
from autoforge.core.event import EventBus
from autoforge.infrastructure.http import (
    ControlPlaneHTTPSettings,
    create_control_plane_app,
)
from autoforge.infrastructure.job import InMemoryJobStore

TOKEN = "test-control-plane-token"


def _write_specifications(root: Path) -> None:
    modules = root / "spec" / "modules"
    modules.mkdir(parents=True)
    (root / "spec" / "project.yaml").write_text(
        """spec_version: "1"
project:
  name: Sample
  package_name: sample
  version: "0.1.0"
application:
  modules:
    - account
""",
        encoding="utf-8",
    )
    (modules / "account.yaml").write_text(
        """spec_version: "1"
module:
  name: account
  display_name: Account
  route_prefix: /account
""",
        encoding="utf-8",
    )


def _client(tmp_path: Path, *, max_request_bytes: int = 4096) -> TestClient:
    _write_specifications(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    service = GenerationSubmissionService(
        source_root=tmp_path,
        output_root=output,
        job_store=InMemoryJobStore(),
        event_bus=EventBus(),
    )
    return TestClient(
        create_control_plane_app(
            service=service,
            settings=ControlPlaneHTTPSettings(
                api_token=TOKEN,
                max_request_bytes=max_request_bytes,
            ),
        )
    )


def _payload(output_path: str = "generated/service") -> dict[str, str]:
    return {
        "project_path": "spec/project.yaml",
        "specifications_path": "spec/modules",
        "output_path": output_path,
    }


def _headers(key: str = "delivery-1") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Idempotency-Key": key,
    }


def test_trigger_is_authenticated_idempotent_and_queryable(tmp_path: Path) -> None:
    client = _client(tmp_path)

    unauthorized = client.post("/v1/generation-jobs", json=_payload())
    first = client.post(
        "/v1/generation-jobs", json=_payload(), headers=_headers()
    )
    second = client.post(
        "/v1/generation-jobs", json=_payload(), headers=_headers()
    )
    job_id = first.json()["job"]["job_id"]
    status_response = client.get(
        f"/v1/generation-jobs/{job_id}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert unauthorized.status_code == 401
    assert first.status_code == 202
    assert first.json()["created"] is True
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["job"]["job_id"] == job_id
    assert status_response.status_code == 200
    assert status_response.json()["job"]["status"] == "pending"


def test_trigger_rejects_key_reuse_missing_key_and_large_body(tmp_path: Path) -> None:
    client = _client(tmp_path, max_request_bytes=256)
    first = client.post(
        "/v1/generation-jobs", json=_payload(), headers=_headers()
    )
    conflict = client.post(
        "/v1/generation-jobs",
        json=_payload("generated/other"),
        headers=_headers(),
    )
    missing_key = client.post(
        "/v1/generation-jobs",
        json=_payload(),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    too_large = client.post(
        "/v1/generation-jobs",
        content=b"x" * 257,
        headers=_headers("delivery-2"),
    )
    (tmp_path / "spec" / "project.yaml").write_text(
        "project: [sensitive-input]", encoding="utf-8"
    )
    invalid_specification = client.post(
        "/v1/generation-jobs",
        json=_payload(),
        headers=_headers("delivery-3"),
    )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert missing_key.status_code == 400
    assert too_large.status_code == 413
    assert invalid_specification.status_code == 400
    assert invalid_specification.json()["detail"] == (
        "Generation specification is invalid"
    )
