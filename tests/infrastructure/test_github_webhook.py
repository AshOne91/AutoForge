from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoforge.application.generation import GenerationSubmissionService
from autoforge.core.event import EventBus
from autoforge.infrastructure.http.github_webhook import (
    GitHubWebhookSettings,
    install_github_webhook_route,
)
from autoforge.infrastructure.job import InMemoryJobStore


def _client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    install_github_webhook_route(
        app,
        service=GenerationSubmissionService(
            source_root=tmp_path,
            output_root=tmp_path / "output",
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
        ),
        settings=GitHubWebhookSettings(
            secret="webhook-secret",
            allowed_repositories=frozenset({"AshOne91/AutoForge"}),
        ),
    )
    return TestClient(app)


def _payload(
    *, repository: str = "AshOne91/AutoForge", ref: str = "refs/heads/main"
) -> bytes:
    return json.dumps(
        {
            "ref": ref,
            "after": "a" * 40,
            "deleted": False,
            "repository": {
                "full_name": repository,
                "clone_url": f"https://github.com/{repository}.git",
            },
        }
    ).encode()


def _headers(
    body: bytes, *, delivery: str = "delivery-1", event: str = "push"
) -> dict[str, str]:
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    return {
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
        "X-Hub-Signature-256": f"sha256={signature}",
    }


def test_signed_push_creates_one_durable_job_per_delivery(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = _payload()
    headers = _headers(body)

    first = client.post("/v1/webhooks/github", content=body, headers=headers)
    second = client.post("/v1/webhooks/github", content=body, headers=headers)

    assert first.status_code == 202
    assert first.json()["created"] is True
    assert second.status_code == 200
    assert second.json() == {
        "accepted": True,
        "job_id": first.json()["job_id"],
        "created": False,
    }


def test_invalid_signature_is_rejected(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = _payload()
    headers = _headers(body)
    headers["X-Hub-Signature-256"] = "sha256=invalid"

    response = client.post("/v1/webhooks/github", content=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid GitHub webhook signature"


def test_unsupported_or_disallowed_delivery_is_ignored(tmp_path: Path) -> None:
    client = _client(tmp_path)

    ping_body = _payload()
    ping = client.post(
        "/v1/webhooks/github",
        content=ping_body,
        headers=_headers(ping_body, event="ping"),
    )
    repository_body = _payload(repository="other/repository")
    repository = client.post(
        "/v1/webhooks/github",
        content=repository_body,
        headers=_headers(repository_body, delivery="delivery-2"),
    )
    ref_body = _payload(ref="refs/heads/develop")
    ref = client.post(
        "/v1/webhooks/github",
        content=ref_body,
        headers=_headers(ref_body, delivery="delivery-3"),
    )

    assert ping.json() == {"accepted": True, "ignored": "unsupported_event"}
    assert repository.json() == {
        "accepted": True,
        "ignored": "repository_not_allowed",
    }
    assert ref.json() == {"accepted": True, "ignored": "ref_not_allowed"}
