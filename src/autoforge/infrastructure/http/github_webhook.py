"""GitHub webhook ingress for durable generation-job submission."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from autoforge.application.generation import (
    GenerationSubmissionService,
    GenerationTriggerRequest,
    IdempotencyConflictError,
)


@dataclass(frozen=True, slots=True)
class GitHubWebhookSettings:
    """Restrict which signed GitHub push deliveries may create jobs."""

    secret: str = field(repr=False)
    allowed_repositories: frozenset[str]
    allowed_refs: frozenset[str] = frozenset({"refs/heads/main"})
    project_path: str = "autoforge.yaml"
    specifications_path: str = "specifications"
    output_path: str = "."
    max_body_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if not self.secret:
            raise ValueError("GitHub webhook secret must not be empty")
        if not self.allowed_repositories:
            raise ValueError("at least one GitHub repository must be allowed")
        if any(not _is_repository_name(value) for value in self.allowed_repositories):
            raise ValueError("repository must use the owner/name form")
        if any(not value.startswith("refs/heads/") for value in self.allowed_refs):
            raise ValueError("allowed refs must be branch refs")
        if self.max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")


def install_github_webhook_route(
    app: FastAPI,
    *,
    service: GenerationSubmissionService,
    settings: GitHubWebhookSettings,
) -> None:
    """Install a signed GitHub push endpoint without adding workflow logic."""

    @app.post("/v1/webhooks/github")
    async def receive_github_webhook(
        request: Request,
        event_name: str | None = Header(default=None, alias="X-GitHub-Event"),
        delivery_id: str | None = Header(default=None, alias="X-GitHub-Delivery"),
        signature: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    ) -> JSONResponse:
        body = await _read_limited_body(request, settings.max_body_bytes)
        _verify_signature(body, signature, settings.secret)

        if delivery_id is None or not delivery_id or len(delivery_id) > 247:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-GitHub-Delivery header is required",
            )
        if event_name != "push":
            return _ignored_response("unsupported_event")

        payload = _parse_push_payload(body)
        if payload["deleted"]:
            return _ignored_response("deleted_ref")
        if payload["repository"] not in settings.allowed_repositories:
            return _ignored_response("repository_not_allowed")
        if payload["ref"] not in settings.allowed_refs:
            return _ignored_response("ref_not_allowed")

        try:
            result = await service.trigger(
                GenerationTriggerRequest(
                    project_path=settings.project_path,
                    specifications_path=settings.specifications_path,
                    output_path=settings.output_path,
                    repository_url=payload["clone_url"],
                    revision=payload["revision"],
                ),
                idempotency_key=f"github:{delivery_id}",
            )
        except IdempotencyConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="GitHub delivery conflicts with an existing job",
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub push payload cannot create a generation job",
            ) from error

        return JSONResponse(
            status_code=(
                status.HTTP_202_ACCEPTED if result.created else status.HTTP_200_OK
            ),
            content={
                "accepted": True,
                "job_id": result.job.job_id,
                "created": result.created,
            },
        )


async def _read_limited_body(request: Request, maximum: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    stream: AsyncIterator[bytes] = request.stream()
    async for chunk in stream:
        size += len(chunk)
        if size > maximum:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request body is too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _verify_signature(body: bytes, signature: str | None, secret: str) -> None:
    if signature is None or not signature.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid GitHub webhook signature",
        )
    expected = (
        "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid GitHub webhook signature",
        )


def _parse_push_payload(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body)
        repository = payload["repository"]
        full_name = repository["full_name"]
        clone_url = repository["clone_url"]
        ref = payload["ref"]
        revision = payload["after"]
        deleted = payload["deleted"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub push payload",
        ) from error
    if not all(
        isinstance(value, str) and value
        for value in (full_name, clone_url, ref, revision)
    ) or not isinstance(deleted, bool):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub push payload",
        )
    return {
        "repository": full_name,
        "clone_url": clone_url,
        "ref": ref,
        "revision": revision,
        "deleted": deleted,
    }


def _ignored_response(reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"accepted": True, "ignored": reason},
    )


def _is_repository_name(value: str) -> bool:
    owner, separator, repository = value.partition("/")
    return bool(owner and separator and repository and "/" not in repository)
