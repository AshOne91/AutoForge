import asyncio
import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path, PurePosixPath
from types import ModuleType
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoforge.application.generation import GenerationSubmissionService
from autoforge.core.event import EventBus
from autoforge.core.specification import (
    ApplicationSpec,
    ControlPlaneHeartbeatSpec,
    DatabaseStoreSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
)
from autoforge.infrastructure.heartbeat import InMemoryServiceHeartbeatStore
from autoforge.infrastructure.http import (
    ControlPlaneHTTPSettings,
    create_control_plane_app,
)
from autoforge.infrastructure.job import InMemoryJobStore
from autoforge.services.generation import FastAPIProjectGenerator

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
            heartbeat_store=InMemoryServiceHeartbeatStore(),
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


def test_remote_trigger_is_accepted_without_local_specification(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/generation-jobs",
        json={
            "project_path": "spec/project.yaml",
            "specifications_path": "spec/modules",
            "output_path": ".",
            "repository_url": "https://github.com/example/service.git",
            "revision": "main",
        },
        headers=_headers("remote-delivery-1"),
    )
    missing_revision = client.post(
        "/v1/generation-jobs",
        json={
            **_payload(),
            "repository_url": "https://github.com/example/service.git",
        },
        headers=_headers("remote-delivery-2"),
    )

    assert response.status_code == 202
    assert response.json()["job"]["units"] == []
    assert missing_revision.status_code == 422


def test_service_heartbeat_is_authenticated_upserted_and_queryable(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    payload = {
        "instance_id": "kis-api-1",
        "service_name": "application",
        "deployed_version": "2026.08.18",
        "dependencies": {"postgres": "ok", "rabbitmq": "degraded"},
    }

    unauthorized = client.post("/v1/service-heartbeats", json=payload)
    first = client.post(
        "/v1/service-heartbeats",
        json=payload,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    second = client.post(
        "/v1/service-heartbeats",
        json={**payload, "deployed_version": "2026.08.19"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    listed = client.get(
        "/v1/service-heartbeats",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert unauthorized.status_code == 401
    assert first.status_code == 200
    assert first.json()["dependencies"] == {"postgres": "ok", "rabbitmq": "degraded"}
    assert second.json()["deployed_version"] == "2026.08.19"
    assert listed.json()["heartbeats"] == [second.json()]


def test_generated_heartbeat_reporter_posts_to_control_plane(
    tmp_path: Path, monkeypatch
) -> None:
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Sample",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(
            databases=[
                DatabaseStoreSpec(name="identity", global_url_env="IDENTITY_URL")
            ],
            services=[
                ServiceSpec(
                    name="session",
                    kind="redis_session",
                    namespace="game_session",
                    ttl_seconds=3600,
                )
            ],
            control_plane_heartbeat=ControlPlaneHeartbeatSpec(enabled=True),
        ),
    )
    rendered = FastAPIProjectGenerator().render(specification)
    reporter_source = rendered[
        PurePosixPath(
            "src/game_server/application/generated/service_heartbeat.py"
        )
    ]
    client = _client(tmp_path)
    logger_module = ModuleType("game_server.application.observability")
    logger_module.LOGGER = __import__("logging").getLogger("test-heartbeat")
    monkeypatch.setitem(sys.modules, "game_server", ModuleType("game_server"))
    monkeypatch.setitem(
        sys.modules, "game_server.application", ModuleType("game_server.application")
    )
    monkeypatch.setitem(
        sys.modules, "game_server.application.observability", logger_module
    )
    monkeypatch.setenv("POD_NAME", "pod@one")
    reporter_path = tmp_path / "service_heartbeat.py"
    reporter_path.write_text(reporter_source, encoding="utf-8")
    loader = SourceFileLoader("generated_service_heartbeat", str(reporter_path))
    module_spec = importlib.util.spec_from_loader(loader.name, loader)
    assert module_spec is not None
    reporter = importlib.util.module_from_spec(module_spec)
    monkeypatch.setitem(sys.modules, loader.name, reporter)
    loader.exec_module(reporter)

    class InlineAsyncio:
        CancelledError = asyncio.CancelledError
        create_task = staticmethod(asyncio.create_task)
        sleep = staticmethod(asyncio.sleep)

        @staticmethod
        async def to_thread(function, *args):
            return function(*args)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"{}"

    def urlopen(request, *, timeout):
        assert timeout == 5
        response = client.post(
            urlsplit(request.full_url).path,
            content=request.data,
            headers=dict(request.header_items()),
        )
        assert response.status_code == 200
        return Response()

    reporter.asyncio = InlineAsyncio
    reporter.urlopen = urlopen

    async def run_reporter() -> None:
        lifespan = reporter.service_heartbeat_lifespan
        async with lifespan(FastAPI()):
            await asyncio.sleep(0)

    monkeypatch.setenv("CONTROL_PLANE_HEARTBEAT_URL", "http://control.local/v1/service-heartbeats")
    monkeypatch.setenv("CONTROL_PLANE_API_TOKEN", TOKEN)
    asyncio.run(run_reporter())

    listed = client.get(
        "/v1/service-heartbeats",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert listed.status_code == 200
    heartbeat = listed.json()["heartbeats"][0]
    assert heartbeat["instance_id"] == "pod-one"
    assert heartbeat["service_name"] == "game_server"
    assert heartbeat["deployed_version"] == "0.1.0"
    assert heartbeat["dependencies"] == {"database": "ok", "session_store": "ok"}
