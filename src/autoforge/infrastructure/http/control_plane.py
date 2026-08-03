from dataclasses import dataclass
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from autoforge.application.generation import (
    GenerationSpecificationError,
    GenerationSubmissionService,
    GenerationTriggerRequest,
    IdempotencyConflictError,
)
from autoforge.core.job import GenerationJob


@dataclass(frozen=True, slots=True)
class ControlPlaneHTTPSettings:
    api_token: str
    max_request_bytes: int = 4096

    def __post_init__(self) -> None:
        if not self.api_token:
            raise ValueError("api_token must not be empty")
        if self.max_request_bytes < 1:
            raise ValueError("max_request_bytes must be positive")


class GenerationTriggerBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_path: str = Field(min_length=1, max_length=1024)
    specifications_path: str = Field(min_length=1, max_length=1024)
    output_path: str = Field(min_length=1, max_length=1024)
    repository_url: str | None = Field(default=None, min_length=1, max_length=2048)
    revision: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_repository_pair(self) -> "GenerationTriggerBody":
        if (self.repository_url is None) != (self.revision is None):
            raise ValueError(
                "repository_url and revision must be provided together"
            )
        return self


class GenerationJobResponse(BaseModel):
    job: GenerationJob
    created: bool | None = None


def create_control_plane_app(
    *,
    service: GenerationSubmissionService,
    settings: ControlPlaneHTTPSettings,
) -> FastAPI:
    app = FastAPI(title="AutoForge Control Plane", version="0.1.0")
    bearer = HTTPBearer(auto_error=False)

    async def require_authentication(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(bearer)
        ],
    ) -> None:
        if (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not compare_digest(credentials.credentials, settings.api_token)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.post(
        "/v1/generation-jobs",
        response_model=GenerationJobResponse,
        dependencies=[Depends(require_authentication)],
    )
    async def trigger_generation(
        request: Request,
        response: Response,
        idempotency_key: Annotated[
            str | None, Header(alias="Idempotency-Key")
        ] = None,
    ) -> GenerationJobResponse:
        if idempotency_key is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key header is required",
            )
        body = await _read_limited_body(request, settings.max_request_bytes)
        try:
            payload = GenerationTriggerBody.model_validate_json(body)
            result = await service.trigger(
                GenerationTriggerRequest(**payload.model_dump()),
                idempotency_key=idempotency_key,
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid request body",
            ) from error
        except GenerationSpecificationError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generation specification is invalid",
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except IdempotencyConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        response.status_code = (
            status.HTTP_202_ACCEPTED if result.created else status.HTTP_200_OK
        )
        return GenerationJobResponse(job=result.job, created=result.created)

    @app.get(
        "/v1/generation-jobs/{job_id}",
        response_model=GenerationJobResponse,
        dependencies=[Depends(require_authentication)],
    )
    async def get_generation(job_id: str) -> GenerationJobResponse:
        job = await service.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GenerationJob not found",
            )
        return GenerationJobResponse(job=job)

    return app


async def _read_limited_body(request: Request, limit: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length header",
            ) from error
        if declared_length < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length header",
            )
        if declared_length > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Request body is too large",
            )
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Request body is too large",
            )
    return bytes(body)
