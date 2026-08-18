from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DependencyStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ServiceHeartbeatReport(BaseModel):
    """Bounded service state reported to the AutoForge Control Plane."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    service_name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    deployed_version: str = Field(min_length=1, max_length=128)
    dependencies: dict[str, DependencyStatus] = Field(default_factory=dict, max_length=16)

    @field_validator("deployed_version")
    @classmethod
    def validate_deployed_version(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("deployed_version must not be empty")
        return value

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(
        cls, value: dict[str, DependencyStatus]
    ) -> dict[str, DependencyStatus]:
        if any(not name or len(name) > 128 for name in value):
            raise ValueError("dependency names must contain 1 to 128 characters")
        return value


class ServiceHeartbeat(ServiceHeartbeatReport):
    """A server-timestamped heartbeat with an expiry owned by the Control Plane."""

    reported_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ServiceHeartbeat":
        if self.reported_at.utcoffset() is None or self.expires_at.utcoffset() is None:
            raise ValueError("heartbeat timestamps must be timezone-aware")
        if self.expires_at <= self.reported_at:
            raise ValueError("expires_at must be after reported_at")
        return self
